"""Bind a listener and hand back the accepted peer address."""

import socket


def accept_one(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind(("127.0.0.1", port))
        server.listen(1)
        _peer, address = server.accept()
        return address
    finally:
        server.close()
