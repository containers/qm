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
#include <sys/syscall.h>
#include <sys/un.h>
#include <unistd.h>

static void console_forward(int listener, const char *path, pid_t parent)
{
	/* In particular, do not leave a child waiting for a console when crun
	 * fails before sending it, or when the foreground runtime is killed.
	 */
	if (prctl(PR_SET_PDEATHSIG, SIGTERM) < 0)
		err(1, "set console parent-death signal");
	if (getppid() != parent)
		_exit(0);

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
	autoclose int master = -1;
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
	close(connection);
	connection = -1;

	/* Crun's container init sends the master before exec. Keep the slave
	 * open while init runs: systemd closes and reopens its console during
	 * startup, and those gaps must not look like the end of the console.
	 * Watch init rather than crun, which waits for this relay to drain.
	 */
	autoclose int init = syscall(SYS_pidfd_open, sender.pid, 0);
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
	struct pollfd fds[] = {
		{.fd = master, .events = POLLIN},
		{.fd = init, .events = POLLIN},
	};

	char buffer[8192];
	for (;;) {
		if (TEMP_FAILURE_RETRY(poll(fds, N_ELEMENTS(fds), -1)) < 0)
			err(1, "poll console");
		if (fds[1].revents) {
			close(slave);
			slave = -1;
			fds[1].fd = -1;
		}
		if (!fds[0].revents)
			continue;
		count = TEMP_FAILURE_RETRY(read(master, buffer, sizeof(buffer)));
		/* A PTY returns EIO once the last slave descriptor is closed. */
		if (count == 0 || (count < 0 && errno == EIO))
			_exit(0);
		if (count < 0)
			err(1, "read console");
		write_all(STDOUT_FILENO, buffer, count);
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
