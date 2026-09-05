"""One handle per iteration of a while loop, each released."""

import http.client


def ingest_http_plain(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    remaining = list(items)
    while remaining:
        remaining.pop()
        with http.client.HTTPConnection(host) as connection:
            connection.request("GET", "/status")
            collected.append(payload)
    return collected
