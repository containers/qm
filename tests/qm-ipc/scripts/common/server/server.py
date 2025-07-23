#!/usr/bin/env python3
"""
UNIX domain socket server that receives timestamp messages.

This script listens on a socket path and accepts incoming client connections.
Each client sends time-stamped messages which the server prints upon receipt.
"""

import os
import socket
import sys

SOCKET_PATH = os.environ.get("SOCKET_PATH", "/run/ipc/ipc.sock")


def systemd_print(*args):
    """Print messages to stdout and flush for journald compatibility."""
    print(*args)
    sys.stdout.flush()


class SimpleServer:
    """UNIX domain socket server."""

    def __init__(self, path: str):
        """
        Initialize the server.

        Args:
            path (str): Path to the UNIX domain socket.
        """
        self.path = path

    def __enter__(self):
        """Enter context manager and start the socket server."""
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if os.path.exists(self.path):
            os.remove(self.path)
        self.sock.bind(self.path)
        self.sock.listen()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and clean up the socket."""
        self.sock.close()
        if os.path.exists(self.path):
            os.remove(self.path)

    def run(self):
        """Run the server loop to accept and print messages from clients."""
        systemd_print("Listening on:", self.path)
        while True:
            conn, _ = self.sock.accept()
            with conn:
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    systemd_print("Received:", data.decode().strip())


def main():
    """Start the SimpleServer using the configured socket path."""
    with SimpleServer(SOCKET_PATH) as server:
        server.run()


if __name__ == "__main__":
    main()
