"""Load payload, releasing the handle in a finally block."""

import http.client


def ingest_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = http.client.HTTPSConnection(host)
    try:
        connection.request("GET", "/health")
        return payload
    except Exception:
        connection.close()
        raise
