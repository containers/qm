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
#include <sys/syscall.h>

static volatile sig_atomic_t pending_signal;

static void forward_signal(int signo)
{
	pending_signal = signo;
}

int exec_with_stdio(char *const argv[])
{
	/* Keep new pipe descriptors clear of the standard descriptor numbers. */
	for (int i = 0; i < 3; i++) {
		if (fcntl(i, F_GETFD) < 0 && errno == EBADF) {
			int fd = open("/dev/null", i == 0 ? O_RDONLY : O_WRONLY);
			if (fd != i)
				err(1, "initialize closed exec stdio");
		}
	}
	int pipes[3][2];
	for (int i = 0; i < 3; i++) {
		if (pipe2(pipes[i], O_CLOEXEC) < 0)
			err(1, "create exec stdio pipe");
	}
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
			if (dup2(pipes[i][i == 0 ? 0 : 1], i) < 0)
				err(1, "set exec stdio");
		}
		for (int i = 0; i < 3; i++) {
			close(pipes[i][0]);
			close(pipes[i][1]);
		}
		execv(argv[0], argv);
		warn("exec %s", argv[0]);
		_exit(1);
	}
	close(pipes[0][0]);
	close(pipes[1][1]);
	close(pipes[2][1]);
	autoclose int input = pipes[0][1];
	autoclose int output = pipes[1][0];
	autoclose int error = pipes[2][0];
	autoclose int pidfd = syscall(SYS_pidfd_open, child, 0);
	if (pidfd < 0 || fcntl(input, F_SETFL, O_NONBLOCK) < 0) {
		kill(child, SIGKILL);
		wait_child(child);
		err(1, "prepare exec stdio relay");
	}
	signal(SIGPIPE, SIG_IGN);
	struct sigaction action = {.sa_handler = forward_signal};
	sigemptyset(&action.sa_mask);
	sigset_t watched, original;
	sigemptyset(&watched);
	for (size_t i = 0; i < 4; i++) {
		const int signals[] = {SIGINT, SIGTERM, SIGHUP, SIGQUIT};
		sigaddset(&watched, signals[i]);
		if (sigaction(signals[i], &action, NULL) < 0)
			err(1, "set exec signal handler");
	}
	if (sigprocmask(SIG_BLOCK, &watched, &original) < 0)
		err(1, "block exec signals");
	char buffer[16384];
	size_t length = 0, offset = 0;
	bool exited = false;
	while (!exited || output >= 0 || error >= 0) {
		if (pending_signal) {
			kill(child, pending_signal);
			pending_signal = 0;
		}
		struct pollfd fds[] = {
			{.fd = exited ? -1 : pidfd, .events = POLLIN},
			{.fd = input >= 0 && length == 0 ? STDIN_FILENO : -1,
			 .events = POLLIN},
			{.fd = input >= 0 && length > 0 ? input : -1, .events = POLLOUT},
			{.fd = output, .events = POLLIN},
			{.fd = error, .events = POLLIN},
		};
		if (ppoll(fds, N_ELEMENTS(fds), NULL, &original) < 0) {
			if (errno == EINTR)
				continue;
			err(1, "poll exec stdio");
		}
		if (fds[0].revents) {
			exited = true;
			if (input >= 0) {
				close(input);
				input = -1;
			}
		}
		if (input >= 0 && fds[1].revents) {
			ssize_t n = TEMP_FAILURE_RETRY(
				read(STDIN_FILENO, buffer, sizeof(buffer)));
			if (n < 0)
				err(1, "read exec stdin");
			length = n;
			offset = 0;
			if (!n) {
				close(input);
				input = -1;
			}
		}
		if (input >= 0 && fds[2].revents) {
			ssize_t n = write(input, buffer + offset, length);
			if (n < 0 && errno == EPIPE) {
				close(input);
				input = -1;
			} else if (n < 0 && errno != EINTR && errno != EAGAIN) {
				err(1, "write exec stdin");
			} else if (n > 0) {
				offset += n;
				length -= n;
			}
		}
		for (int i = 0; i < 2; i++) {
			int *fd = i == 0 ? &output : &error;
			if (*fd < 0 || !fds[3 + i].revents)
				continue;
			char data[16384];
			ssize_t n = TEMP_FAILURE_RETRY(read(*fd, data, sizeof(data)));
			if (n < 0)
				err(1, "read exec output");
			if (n)
				write_all(i + 1, data, n);
			else {
				close(*fd);
				*fd = -1;
			}
		}
	}
	int status = wait_child(child);
	return status < 0 ? 1 : status;
}
