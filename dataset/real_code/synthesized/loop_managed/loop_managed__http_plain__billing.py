"""One handle per item, each released inside the loop."""

import http.client


def billing_http_plain(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        with http.client.HTTPConnection(host) as connection:
            connection.request("GET", "/status")
            collected.append(payload)
    return collected
