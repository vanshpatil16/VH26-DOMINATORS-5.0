"""Two independent handles, each released in its own finally."""

import socket


def billing_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = socket.create_connection((host, port))
    try:
        target = socket.create_connection((host, port))
        try:
            source.sendall(payload)
            target.sendall(payload)
        finally:
            target.close()
    finally:
        source.close()
    return payload
