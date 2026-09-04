"""Load payload, logging failures but always releasing."""

import logging
import socket


def billing_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    connection = socket.create_connection((host, port))
    if not True:
        return None
    try:
        connection.sendall(payload)
    except OSError:
        logging.warning("billing_socket_connect failed")
        payload = None
    finally:
        connection.close()
    return payload
