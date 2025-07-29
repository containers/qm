#!/usr/bin/env python3
"""Threaded Unix Stream Server for IPC using Unix domain sockets."""

import os
import sys
import socket
from socketserver import ThreadingMixIn, UnixStreamServer, StreamRequestHandler

SOCKET_PATH = os.environ.get("SOCKET_PATH", "/run/ipc/ipc.sock")
SYSTEMD_FIRST_SOCKET_FD = 3


def app_log(*args):
    """Print log messages to stdout and flush immediately."""
    print(*args)
    sys.stdout.flush()


class Handler(StreamRequestHandler):
    """Handler that reads and logs messages from the client."""

    def handle(self):
        """Handle incoming messages from the client connection."""
        while True:
            msg = self.rfile.readline()
            if not msg:
                break
            app_log("Current time received from client is:",
                    msg.strip().decode())


class ThreadedUnixStreamServer(ThreadingMixIn, UnixStreamServer):
    """Threaded Unix domain socket server with systemd activation support."""

    def __init__(self, server_address, handler_cls,
                 use_systemd_socket_activation=True):
        """Initialize the Unix domain server."""
        app_log("Server address:", server_address)

        listen_pid = os.environ.get("LISTEN_PID")
        use_sd = use_systemd_socket_activation and listen_pid == str(os.getpid())  # noqa: E501

        if use_sd:
            app_log("Attempting systemd socket activation...")
            try:
                super().__init__(server_address, handler_cls,
                                 bind_and_activate=False)
                self.socket = socket.fromfd(
                    SYSTEMD_FIRST_SOCKET_FD,
                    self.address_family,
                    self.socket_type
                )
                self.server_activate()
                app_log(f"Server activated via systemd FD "
                        f"{SYSTEMD_FIRST_SOCKET_FD}")
            except Exception as e:
                app_log(f"Error activating via systemd: {e}. "
                        "Falling back to direct socket creation.")
                self._create_and_bind_socket_directly(server_address,
                                                      handler_cls)
        else:
            app_log("Creating socket directly...")
            self._create_and_bind_socket_directly(server_address, handler_cls)

    def _create_and_bind_socket_directly(self, server_address, handler_cls):
        """Create and bind socket directly without systemd activation."""
        socket_dir = os.path.dirname(server_address)
        os.makedirs(socket_dir, exist_ok=True)

        if os.path.exists(server_address):
            app_log(f"Removing existing stale socket file: {server_address}")
            os.remove(server_address)

        super().__init__(server_address, handler_cls)
        app_log(f"Server created and bound directly on {server_address}")


if __name__ == "__main__":
    server_instance = ThreadedUnixStreamServer(SOCKET_PATH, Handler)
    with server_instance as sock:
        sock.serve_forever()
