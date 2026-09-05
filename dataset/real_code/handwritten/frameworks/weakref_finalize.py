"""Cleanup bound to the lifetime of the owning object."""

import socket
import weakref


class Probe:
    def __init__(self, host, port):
        sock = socket.create_connection((host, port))
        self._sock = sock
        weakref.finalize(self, sock.close)

    def ping(self):
        self._sock.sendall(b"ping")
