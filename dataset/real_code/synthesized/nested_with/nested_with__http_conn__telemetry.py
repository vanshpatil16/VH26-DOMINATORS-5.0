"""Two handles, both owned by nested context managers."""

import http.client


def telemetry_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with http.client.HTTPSConnection(host) as primary:
        with http.client.HTTPSConnection(host) as secondary:
            primary.request("GET", "/health")
            secondary.request("GET", "/health")
    return payload
