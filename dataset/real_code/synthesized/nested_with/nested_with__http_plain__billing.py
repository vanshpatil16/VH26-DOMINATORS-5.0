"""Two handles, both owned by nested context managers."""

import http.client


def billing_http_plain(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with http.client.HTTPConnection(host) as primary:
        with http.client.HTTPConnection(host) as secondary:
            primary.request("GET", "/status")
            secondary.request("GET", "/status")
    return payload
