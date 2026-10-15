/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2026 Alexander Larsson
 * See LICENSE for the full license text.
 */
#define _GNU_SOURCE
#include "qm-exec.h"
#include "qm-utils.h"

#include <err.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>

static const int exec_signals[] = {SIGINT, SIGTERM, SIGHUP, SIGQUIT};
static volatile sig_atomic_t pending_signals;

typedef struct {
	int source, destination;
	bool source_socket, destination_socket;
	char buffer[16384];
	size_t offset, length;
} Stream;

static void forward_signal(int signo)
{
	pending_signals |= 1U << signo;
}

static void close_stream_fd(int *fd)
{
	if (*fd >= 0)
		close(*fd);
	*fd = -1;
}

static void close_stream(Stream *stream)
{
	close_stream_fd(&stream->source);
	close_stream_fd(&stream->destination);
	stream->length = 0;
}

static void nonblocking(int fd)
{
	int flags = fcntl(fd, F_GETFL);
	if (flags < 0 || fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0)
		err(1, "set exec pipe nonblocking");
}

static int relay_fd(int fd, bool input, bool *is_socket)
{
	struct stat st;
	if (fstat(fd, &st) < 0)
		err(1, "stat exec stdio");
	*is_socket = S_ISSOCK(st.st_mode);
	int copy;
	if (S_ISFIFO(st.st_mode) || isatty(fd)) {
		/* A dup shares status flags with the caller. Reopen pipes and terminals
		 * to make only our own description nonblocking. Sockets use MSG_DONTWAIT
		 * below; regular files keep their shared offset and append semantics.
		 */
		autofree char *path = xasprintf("/proc/self/fd/%d", fd);
		copy = open(path, (input ? O_RDONLY : O_WRONLY) | O_NONBLOCK | O_NOCTTY |
					  O_CLOEXEC);
	} else {
		copy = fcntl(fd, F_DUPFD_CLOEXEC, 3);
	}
	if (copy < 0)
		err(1, "copy exec stdio");
	return copy;
}

static void read_stream(Stream *stream)
{
	ssize_t n = stream->source_socket ? recv(stream->source, stream->buffer,
						 sizeof(stream->buffer), MSG_DONTWAIT)
					  : read(stream->source, stream->buffer,
						 sizeof(stream->buffer));
	if (n < 0) {
		if (errno != EINTR && errno != EAGAIN)
			err(1, "read exec stream");
	} else if (!n) {
		close_stream_fd(&stream->source);
		close_stream_fd(&stream->destination);
	} else {
		stream->length = n;
		stream->offset = 0;
	}
}

static void write_stream(Stream *stream, bool input)
{
	const char *data = stream->buffer + stream->offset;
	ssize_t n = stream->destination_socket
			    ? send(stream->destination, data, stream->length,
				   MSG_DONTWAIT | MSG_NOSIGNAL)
			    : write(stream->destination, data, stream->length);
	if (n < 0 && input && errno == EPIPE) {
		close_stream(stream);
	} else if (n < 0 && errno != EINTR && errno != EAGAIN) {
		err(1, "write exec stream");
	} else if (n > 0) {
		stream->offset += n;
		stream->length -= n;
	}
}

int exec_with_stdio(char *const argv[], bool interactive)
{
	/* Keep new pipe descriptors clear of the standard descriptor numbers. */
	for (int i = 0; i < 3; i++) {
		if (fcntl(i, F_GETFD) < 0 && errno == EBADF) {
			int fd = open("/dev/null", i == 0 ? O_RDONLY : O_WRONLY);
			if (fd != i)
				err(1, "initialize closed exec stdio");
		}
	}
	autoclose int null_input = open("/dev/null", O_RDONLY | O_CLOEXEC);
	if (null_input < 0)
		err(1, "open exec /dev/null");
	int pipes[3][2] = {{-1, -1}, {-1, -1}, {-1, -1}};
	for (int i = interactive ? 0 : 1; i < 3; i++) {
		if (pipe2(pipes[i], O_CLOEXEC) < 0)
			err(1, "create exec stdio pipe");
	}
	sigset_t watched, original;
	sigemptyset(&watched);
	for (size_t i = 0; i < N_ELEMENTS(exec_signals); i++)
		sigaddset(&watched, exec_signals[i]);
	/* Queue signals until the parent has installed its handlers, including
	 * signals received immediately after the fork.
	 */
	if (sigprocmask(SIG_BLOCK, &watched, &original) < 0)
		err(1, "block exec signals");
	pending_signals = 0;
	pid_t parent = getpid();
	pid_t child = fork();
	if (child < 0)
		err(1, "fork exec runtime");
	if (!child) {
		if (prctl(PR_SET_PDEATHSIG, SIGTERM) < 0 || getppid() != parent)
			_exit(1);
		if (setpgid(0, 0) < 0)
			err(1, "set exec process group");
		for (int i = 0; i < 3; i++) {
			int fd = i == 0 ? (interactive ? pipes[0][0] : null_input)
					: pipes[i][1];
			if (dup2(fd, i) < 0)
				err(1, "set exec stdio");
		}
		for (int i = 0; i < 3; i++) {
			if (pipes[i][0] >= 0)
				close(pipes[i][0]);
			if (pipes[i][1] >= 0)
				close(pipes[i][1]);
		}
		if (sigprocmask(SIG_SETMASK, &original, NULL) < 0)
			err(1, "restore exec signals");
		execv(argv[0], argv);
		warn("exec %s", argv[0]);
		_exit(1);
	}
	if (interactive)
		close(pipes[0][0]);
	close(pipes[1][1]);
	close(pipes[2][1]);
	autoclose int pidfd = syscall(SYS_pidfd_open, child, 0);
	if (pidfd < 0) {
		kill(child, SIGKILL);
		wait_child(child);
		err(1, "prepare exec stdio relay");
	}
	Stream streams[3] = {
		{.source = -1, .destination = pipes[0][1]},
		{.source = pipes[1][0]},
		{.source = pipes[2][0]},
	};
	if (interactive) {
		streams[0].source = relay_fd(0, true, &streams[0].source_socket);
		nonblocking(streams[0].destination);
	}
	for (int i = 1; i < 3; i++) {
		streams[i].destination =
			relay_fd(i, false, &streams[i].destination_socket);
		nonblocking(streams[i].source);
	}
	struct sigaction action = {.sa_handler = forward_signal, .sa_mask = watched};
	struct sigaction previous[N_ELEMENTS(exec_signals)], previous_pipe;
	for (size_t i = 0; i < N_ELEMENTS(exec_signals); i++)
		if (sigaction(exec_signals[i], &action, &previous[i]) < 0)
			err(1, "set exec signal handler");
	struct sigaction ignore = {.sa_handler = SIG_IGN};
	sigemptyset(&ignore.sa_mask);
	if (sigaction(SIGPIPE, &ignore, &previous_pipe) < 0)
		err(1, "ignore exec SIGPIPE");
	bool exited = false, interrupted = false;
	while (!exited || streams[1].source >= 0 || streams[1].length ||
	       streams[2].source >= 0 || streams[2].length) {
		for (size_t i = 0; i < N_ELEMENTS(exec_signals); i++) {
			if (pending_signals & (1U << exec_signals[i])) {
				kill(child, exec_signals[i]);
				interrupted = true;
			}
		}
		pending_signals = 0;
		/* On cancellation, do not let an unread output pipe prevent exit after
		 * the child has stopped. Ordinary completion drains both output streams.
		 */
		if (exited && interrupted)
			break;
		struct pollfd fds[7] = {{.fd = exited ? -1 : pidfd, .events = POLLIN}};
		for (int i = 0; i < 3; i++) {
			Stream *stream = &streams[i];
			fds[1 + 2 * i] = (struct pollfd){
				.fd = stream->length ? -1 : stream->source,
				.events = POLLIN};
			fds[2 + 2 * i] = (struct pollfd){
				.fd = stream->length ? stream->destination : -1,
				.events = POLLOUT};
		}
		if (ppoll(fds, N_ELEMENTS(fds), NULL, &original) < 0) {
			if (errno == EINTR)
				continue;
			err(1, "poll exec stdio");
		}
		if (fds[0].revents) {
			exited = true;
			close_stream(&streams[0]);
		}
		for (int i = 0; i < 3; i++) {
			Stream *stream = &streams[i];
			if (stream->source >= 0 && fds[1 + 2 * i].revents)
				read_stream(stream);
			if (stream->destination >= 0 && fds[2 + 2 * i].revents)
				write_stream(stream, i == 0);
		}
	}
	for (int i = 0; i < 3; i++)
		close_stream(&streams[i]);
	int status = wait_child(child);
	for (size_t i = 0; i < N_ELEMENTS(exec_signals); i++)
		if (sigaction(exec_signals[i], &previous[i], NULL) < 0)
			err(1, "restore exec signal handler");
	if (sigaction(SIGPIPE, &previous_pipe, NULL) < 0 ||
	    sigprocmask(SIG_SETMASK, &original, NULL) < 0)
		err(1, "restore exec signals");
	return status < 0 ? 1 : status;
}
