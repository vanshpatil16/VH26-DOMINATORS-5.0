"""Two handles, both owned by nested context managers."""

import socket


def telemetry_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with socket.create_connection((host, port)) as primary:
        with socket.create_connection((host, port)) as secondary:
            primary.sendall(payload)
            secondary.sendall(payload)
    return payload
