"""One handle per item, released in a finally."""

import socket


def billing_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        connection = socket.create_connection((host, port))
        try:
            connection.sendall(payload)
            collected.append(payload)
        finally:
            connection.close()
    return collected
