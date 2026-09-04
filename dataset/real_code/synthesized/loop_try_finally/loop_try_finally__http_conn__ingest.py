"""One handle per item, released in a finally."""

import http.client


def ingest_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        connection = http.client.HTTPSConnection(host)
        try:
            connection.request("GET", "/health")
            collected.append(payload)
        finally:
            connection.close()
    return collected
