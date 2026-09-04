"""A plain generator whose finally releases the handle on abandon."""

import socket


def ingest_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    connection = socket.create_connection((host, port))
    try:
        connection.sendall(payload)
        for item in items:
            yield item
    finally:
        connection.close()
