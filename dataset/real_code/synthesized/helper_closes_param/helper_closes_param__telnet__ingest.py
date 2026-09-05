"""Cleanup delegated to a helper called on every path."""

import telnetlib


def _release(client):
    client.close()


def ingest_telnet(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = telnetlib.Telnet(host)
    try:
        payload = client.read_until(b"$")
        return payload
    finally:
        _release(client)
