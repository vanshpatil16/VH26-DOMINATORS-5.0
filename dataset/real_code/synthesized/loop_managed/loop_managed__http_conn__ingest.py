"""One handle per item, each released inside the loop."""

import http.client


def ingest_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        with http.client.HTTPSConnection(host) as connection:
            connection.request("GET", "/health")
            collected.append(payload)
    return collected
