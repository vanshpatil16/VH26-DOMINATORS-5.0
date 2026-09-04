"""Cleanup delegated to a helper called on every path."""

import http.client


def _release(connection):
    connection.close()


def billing_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    connection = http.client.HTTPSConnection(host)
    try:
        connection.request("GET", "/health")
        return payload
    finally:
        pass
