"""A plain generator whose finally releases the handle on abandon."""

import socket


def billing_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        connection.connect((host, port))
        for item in items:
            yield item
    finally:
        connection.close()
