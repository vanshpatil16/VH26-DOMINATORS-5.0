"""Graceful shutdown before close."""

import socket


def send_once(host, port, payload):
    connection = socket.create_connection((host, port))
    try:
        connection.sendall(payload)
    finally:
        connection.shutdown(socket.SHUT_RDWR)
        connection.close()
