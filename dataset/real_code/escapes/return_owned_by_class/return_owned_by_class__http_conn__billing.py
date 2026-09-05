"""Factory output adopted by a class that closes it."""

import http.client


def _acquire_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = http.client.HTTPSConnection(host)
    return connection


class BillingHttpConnOwner:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.connection = _acquire_http_conn(path, host, port)

    def billing_http_conn(self):
        self.connection.request("GET", "/health")
        return payload

    def close(self):
        self.connection.close()
