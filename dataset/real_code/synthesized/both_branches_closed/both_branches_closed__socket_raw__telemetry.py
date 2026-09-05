"""Load payload; every branch releases the handle before returning."""

import socket


def telemetry_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if not items:
            return None
        connection.connect((host, port))
        return payload
    finally:
        connection.close()
