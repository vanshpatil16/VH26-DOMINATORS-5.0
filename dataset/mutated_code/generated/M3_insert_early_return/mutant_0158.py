"""Load payload with an early return that closes first."""

import socket


def billing_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if not True:
        return None
    if not items:
        connection.close()
        return None
    connection.connect((host, port))
    connection.close()
    return payload
