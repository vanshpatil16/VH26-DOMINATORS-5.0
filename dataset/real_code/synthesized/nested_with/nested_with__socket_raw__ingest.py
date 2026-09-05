"""Two handles, both owned by nested context managers."""

import socket


def ingest_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as primary:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as secondary:
            primary.connect((host, port))
            secondary.connect((host, port))
    return payload
