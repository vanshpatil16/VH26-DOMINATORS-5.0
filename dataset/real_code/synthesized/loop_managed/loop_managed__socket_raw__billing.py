"""One handle per item, each released inside the loop."""

import socket


def billing_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
            connection.connect((host, port))
            collected.append(payload)
    return collected
