"""Load payload with an early return that closes first."""

import http.client


def ingest_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = http.client.HTTPSConnection(host)
    if not items:
        connection.close()
        return None
    connection.request("GET", "/health")
    connection.close()
    return payload
