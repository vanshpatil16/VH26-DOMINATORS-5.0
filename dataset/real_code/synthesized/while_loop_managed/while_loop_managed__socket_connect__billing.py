"""One handle per iteration of a while loop, each released."""

import socket


def billing_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    remaining = list(items)
    while remaining:
        remaining.pop()
        with socket.create_connection((host, port)) as connection:
            connection.sendall(payload)
            collected.append(payload)
    return collected
