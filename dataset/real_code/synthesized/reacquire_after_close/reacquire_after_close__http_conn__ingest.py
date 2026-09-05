"""Acquire, release, then acquire a second time and release again."""

import http.client


def ingest_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = http.client.HTTPSConnection(host)
    try:
        connection.request("GET", "/health")
    finally:
        connection.close()
    retry = http.client.HTTPSConnection(host)
    try:
        retry.request("GET", "/health")
    finally:
        retry.close()
    return payload
