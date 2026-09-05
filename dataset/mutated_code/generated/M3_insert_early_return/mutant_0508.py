"""Load payload, logging failures but always releasing."""

import logging
import socket


def telemetry_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = socket.create_connection((host, port))
    if not True:
        return None
    try:
        connection.sendall(payload)
    except OSError:
        logging.warning("telemetry_socket_connect failed")
        payload = None
    finally:
        connection.close()
    return payload
