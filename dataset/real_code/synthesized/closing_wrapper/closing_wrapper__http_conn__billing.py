"""Load payload through contextlib.closing."""

import contextlib
import http.client


def billing_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with contextlib.closing(http.client.HTTPSConnection(host)) as connection:
        connection.request("GET", "/health")
    return payload
