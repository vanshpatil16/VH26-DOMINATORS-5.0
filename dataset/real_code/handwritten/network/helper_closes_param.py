"""The cleanup lives in a helper that is called on every path."""

import socket


def _shutdown(connection):
    connection.close()


def request(host, port, payload):
    connection = socket.create_connection((host, port))
    try:
        connection.sendall(payload)
        return connection.recv(1024)
    finally:
        _shutdown(connection)
