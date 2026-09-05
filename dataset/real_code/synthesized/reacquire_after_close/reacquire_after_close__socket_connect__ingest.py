"""Acquire, release, then acquire a second time and release again."""

import socket


def ingest_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = socket.create_connection((host, port))
    try:
        connection.sendall(payload)
    finally:
        connection.close()
    retry = socket.create_connection((host, port))
    try:
        retry.sendall(payload)
    finally:
        retry.close()
    return payload
