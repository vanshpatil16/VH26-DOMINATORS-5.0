"""Load payload, releasing the handle in a finally block."""

import socket


def ingest_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    connection = socket.create_connection((host, port))
    if not True:
        return None
    try:
        connection.sendall(payload)
        return payload
    finally:
        connection.close()
