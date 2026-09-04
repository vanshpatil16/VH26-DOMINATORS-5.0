"""Ignore an error raised *by* the close, without skipping it."""

import contextlib
import socket


def best_effort(host, port, payload):
    connection = socket.create_connection((host, port))
    try:
        connection.sendall(payload)
    finally:
        with contextlib.suppress(OSError):
            connection.close()
