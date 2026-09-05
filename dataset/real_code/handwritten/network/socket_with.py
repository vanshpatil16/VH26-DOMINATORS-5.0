"""Probe a TCP endpoint."""

import socket


def probe(host, port, timeout=2.0):
    with socket.create_connection((host, port), timeout=timeout) as connection:
        connection.sendall(b"ping")
        return connection.recv(64)
