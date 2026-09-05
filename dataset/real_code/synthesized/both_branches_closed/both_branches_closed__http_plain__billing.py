"""Load payload; every branch releases the handle before returning."""

import http.client


def billing_http_plain(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = http.client.HTTPConnection(host)
    try:
        if not items:
            return None
        connection.request("GET", "/status")
        return payload
    finally:
        connection.close()
