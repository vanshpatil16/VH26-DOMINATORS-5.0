"""Two independent handles, each released in its own finally."""

import http.client


def ingest_http_plain(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = http.client.HTTPConnection(host)
    try:
        target = http.client.HTTPConnection(host)
        try:
            source.request("GET", "/status")
            target.request("GET", "/status")
        finally:
            target.close()
    finally:
        source.close()
    return payload
