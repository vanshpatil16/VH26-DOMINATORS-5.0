"""Load payload with an ExitStack owning the handle."""

import contextlib
import http.client


def billing_http_plain(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        connection = stack.enter_context(contextlib.closing(http.client.HTTPConnection(host)))
        connection.request("GET", "/status")
        return payload
