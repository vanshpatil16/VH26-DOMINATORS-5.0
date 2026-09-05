"""A plain generator whose finally releases the handle on abandon."""

import http.client


def telemetry_http_plain(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = http.client.HTTPConnection(host)
    try:
        connection.request("GET", "/status")
        for item in items:
            yield item
    finally:
        connection.close()
