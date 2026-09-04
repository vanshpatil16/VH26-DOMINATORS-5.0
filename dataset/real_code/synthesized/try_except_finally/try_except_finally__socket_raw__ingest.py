"""Load payload, logging failures but always releasing."""

import logging
import socket


def ingest_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        connection.connect((host, port))
    except OSError:
        logging.warning("ingest_socket_raw failed")
        payload = None
    finally:
        connection.close()
    return payload
