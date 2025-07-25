#!/usr/bin/env python3
"""Client script to send messages over a UNIX domain socket."""

import datetime
import os
import socket
import sys
import time

SOCKET_PATH = os.environ.get("SOCKET_PATH", "/run/ipc/ipc.sock")


def systemd_print(*args):
    """Print to stdout and flush, useful for systemd logging."""
    print(*args)
    sys.stdout.flush()


class SimpleMessage:
    """Represents a simple message with the current timestamp."""

    def __init__(self):
        """Initialize the message with the current datetime."""
        self.now = datetime.datetime.now()

    def __str__(self) -> str:
        """Return the formatted time string."""
        return self.now.strftime("%H:%M:%S") + os.linesep

    def to_bytes(self) -> bytes:
        """Return the message as bytes."""
        return self.__str__().encode()


def send_loop():
    """Connect to the UNIX socket and send messages in a loop."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        systemd_print("Connecting to:", SOCKET_PATH)
        sock.connect(SOCKET_PATH)

        while True:
            msg = SimpleMessage().to_bytes()
            systemd_print("Sending message:", msg)
            sock.sendall(msg)
            time.sleep(1)


if __name__ == "__main__":
    while True:
        try:
            send_loop()
        except OSError as e:
            systemd_print("Connection failed:", e)
            systemd_print("Retrying...")
            time.sleep(5)
