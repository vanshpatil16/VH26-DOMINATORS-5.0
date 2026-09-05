"""Load payload with an early return that closes first."""

import telnetlib


def ingest_telnet(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = telnetlib.Telnet(host)
    if not items:
        client.close()
        return None
    payload = client.read_until(b"$")
    client.close()
    return payload
