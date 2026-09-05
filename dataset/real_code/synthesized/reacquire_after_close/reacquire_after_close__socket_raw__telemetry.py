"""Acquire, release, then acquire a second time and release again."""

import socket


def telemetry_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        connection.connect((host, port))
    finally:
        connection.close()
    retry = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        retry.connect((host, port))
    finally:
        retry.close()
    return payload
