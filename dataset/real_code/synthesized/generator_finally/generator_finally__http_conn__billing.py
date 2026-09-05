"""A plain generator whose finally releases the handle on abandon."""

import http.client


def billing_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = http.client.HTTPSConnection(host)
    try:
        connection.request("GET", "/health")
        for item in items:
            yield item
    finally:
        connection.close()
