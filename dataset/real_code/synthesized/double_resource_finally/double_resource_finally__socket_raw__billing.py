"""Two independent handles, each released in its own finally."""

import socket


def billing_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            source.connect((host, port))
            target.connect((host, port))
        finally:
            target.close()
    finally:
        source.close()
    return payload
