/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */

#define _GNU_SOURCE
#include "qm-console.h"
#include "qm-utils.h"

#include <err.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/un.h>
#include <time.h>
#include <unistd.h>

typedef struct {
	int master;
	pid_t sender_pid;
} ConsoleMessage;

static int64_t monotonic_msec(void)
{
	struct timespec now;
	if (clock_gettime(CLOCK_MONOTONIC, &now) < 0)
		err(1, "get console monotonic time");
	return (int64_t)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

static int console_output(bool *is_socket)
{
	struct stat st;
	if (fstat(STDOUT_FILENO, &st) < 0)
		err(1, "stat console output");
	*is_socket = S_ISSOCK(st.st_mode);
	int fd;
	unsigned int pty_number;
	bool terminal = isatty(STDOUT_FILENO);
	if (terminal && ioctl(STDOUT_FILENO, TIOCGPTN, &pty_number) == 0)
		errx(1, "PTY masters are not supported for console output");
	if (S_ISFIFO(st.st_mode) || terminal) {
		/* Reopen pipes and terminal slaves so O_NONBLOCK does not affect the
		 * caller. PTY masters cannot be reopened independently and are rejected
		 * above. Sockets use MSG_DONTWAIT; files retain shared offsets and O_APPEND.
		 */
		fd = open("/proc/self/fd/1",
			  O_WRONLY | O_NONBLOCK | O_NOCTTY | O_CLOEXEC);
	} else {
		fd = fcntl(STDOUT_FILENO, F_DUPFD_CLOEXEC, 3);
	}
	if (fd < 0)
		err(1, "copy console output");
	return fd;
}

/* Consume listener and return an owned master descriptor and its sender PID. */
static ConsoleMessage receive_console(int listener, const char *path)
{
	autoclose int connection =
		TEMP_FAILURE_RETRY(accept4(listener, NULL, NULL, SOCK_CLOEXEC));
	if (connection < 0)
		err(1, "accept console");
	close(listener);
	unlink(path);

	char byte;
	struct iovec iov = {.iov_base = &byte, .iov_len = sizeof(byte)};
	union {
		struct cmsghdr alignment;
		char bytes[CMSG_SPACE(sizeof(int)) + CMSG_SPACE(sizeof(struct ucred))];
	} control;
	struct msghdr message = {
		.msg_iov = &iov,
		.msg_iovlen = 1,
		.msg_control = control.bytes,
		.msg_controllen = sizeof(control.bytes),
	};
	ssize_t count =
		TEMP_FAILURE_RETRY(recvmsg(connection, &message, MSG_CMSG_CLOEXEC));
	if (count < 0)
		err(1, "receive console");
	if (count == 0 || (message.msg_flags & MSG_CTRUNC))
		errx(1, "incomplete console message from crun");
	int master = -1;
	struct ucred sender = {0};
	for (struct cmsghdr *header = CMSG_FIRSTHDR(&message); header;
	     header = CMSG_NXTHDR(&message, header)) {
		if (header->cmsg_level != SOL_SOCKET)
			continue;
		if (header->cmsg_type == SCM_RIGHTS &&
		    header->cmsg_len == CMSG_LEN(sizeof(int)))
			memcpy(&master, CMSG_DATA(header), sizeof(master));
		else if (header->cmsg_type == SCM_CREDENTIALS &&
			 header->cmsg_len == CMSG_LEN(sizeof(sender)))
			memcpy(&sender, CMSG_DATA(header), sizeof(sender));
	}
	if (master < 0 || sender.pid <= 0)
		errx(1, "crun did not send a console descriptor and credentials");
	return (ConsoleMessage){.master = master, .sender_pid = sender.pid};
}

static void console_forward(int listener, const char *path, pid_t parent)
{
	/* In particular, do not leave a child waiting for a console when crun
	 * fails before sending it, or when the foreground runtime is killed.
	 */
	if (prctl(PR_SET_PDEATHSIG, SIGTERM) < 0)
		err(1, "set console parent-death signal");
	if (getppid() != parent)
		_exit(0);

	const ConsoleMessage console = receive_console(listener, path);
	autoclose int master = console.master;

	/* Crun's container init sends the master before exec. Keep the slave
	 * open while init runs: systemd closes and reopens its console during
	 * startup, and those gaps must not look like the end of the console.
	 * Watch init rather than crun, which waits for this relay to drain.
	 */
	autoclose int init = syscall(SYS_pidfd_open, console.sender_pid, 0);
	/* An init that exits immediately may already have been reaped by crun.
	 * Its console still has to be drained, without holding the slave open.
	 */
	if (init < 0 && errno != ESRCH)
		err(1, "open console init pidfd");
	autoclose int slave = -1;
	if (init >= 0) {
		slave = ioctl(master, TIOCGPTPEER, O_RDWR | O_NOCTTY | O_CLOEXEC);
		if (slave < 0)
			err(1, "open console slave");
	}
	bool output_socket;
	autoclose int output = console_output(&output_socket); /* Non-blocking stdout */
	bool exited = init < 0;
	int64_t deadline = exited ? monotonic_msec() + 1000 : 0;
	char buffer[8192];
	size_t offset = 0, length = 0;
	for (;;) {
		struct pollfd fds[] = {
			{.fd = length ? -1 : master, .events = POLLIN},
			{.fd = exited ? -1 : init, .events = POLLIN},
			{.fd = length ? output : -1, .events = POLLOUT},
		};
		/* Drain final diagnostics, but give up after a second without progress
		 * once init exits. Readiness and EINTR do not count as progress.
		 */
		int timeout = -1;
		if (exited) {
			int64_t remaining = deadline - monotonic_msec();
			if (remaining <= 0)
				_exit(0);
			timeout = remaining;
		}
		int ready = poll(fds, N_ELEMENTS(fds), timeout);
		if (ready < 0) {
			if (errno == EINTR)
				continue;
			err(1, "poll console");
		}
		if (!ready)
			_exit(0);
		if (fds[1].revents) {
			close(slave);
			slave = -1;
			exited = true;
			deadline = monotonic_msec() + 1000;
		}
		if (fds[0].revents) {
			ssize_t count = TEMP_FAILURE_RETRY(read(master, buffer, sizeof(buffer)));
			/* A PTY returns EIO once the last slave descriptor is closed. */
			if (count == 0 || (count < 0 && errno == EIO))
				_exit(0);
			if (count < 0)
				err(1, "read console");
			offset = 0;
			length = count;
		}
		if (fds[2].revents) {
			ssize_t count = output_socket ? send(output, buffer + offset, length,
						     MSG_DONTWAIT | MSG_NOSIGNAL)
					      : write(output, buffer + offset, length);
			if (count < 0) {
				if (errno != EINTR && errno != EAGAIN)
					err(1, "write console");
			} else if (count > 0) {
				offset += count;
				length -= count;
				if (exited)
					deadline = monotonic_msec() + 1000;
			}
		}
	}
}

pid_t console_start(const char *path)
{
	struct sockaddr_un address = {.sun_family = AF_UNIX};
	if (strlen(path) >= sizeof(address.sun_path)) {
		warnx("console socket path too long: %s", path);
		return -1;
	}
	strcpy(address.sun_path, path);
	/* Startup may be continuing after incomplete cleanup. */
	if (unlink(path) < 0 && errno != ENOENT) {
		warn("remove old console socket %s", path);
		return -1;
	}
	int passcred = 1;
	autoclose int listener = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
	if (listener < 0 ||
	    bind(listener, (struct sockaddr *)&address, sizeof(address)) < 0 ||
	    setsockopt(listener, SOL_SOCKET, SO_PASSCRED, &passcred, sizeof(passcred)) <
		    0 ||
	    listen(listener, 1) < 0) {
		warn("listen on console socket %s", path);
		return -1;
	}

	pid_t parent = getpid();
	pid_t child = fork();
	if (child < 0)
		warn("fork console relay");
	else if (child == 0)
		console_forward(listener, path, parent);
	return child;
}
