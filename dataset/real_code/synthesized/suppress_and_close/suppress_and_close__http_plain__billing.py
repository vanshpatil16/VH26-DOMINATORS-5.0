"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import http.client


def billing_http_plain(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = http.client.HTTPConnection(host)
    try:
        with contextlib.suppress(OSError):
            connection.request("GET", "/status")
    finally:
        connection.close()
    return payload
