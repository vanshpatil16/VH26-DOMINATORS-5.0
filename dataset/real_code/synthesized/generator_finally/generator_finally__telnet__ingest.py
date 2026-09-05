"""A plain generator whose finally releases the handle on abandon."""

import telnetlib


def ingest_telnet(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = telnetlib.Telnet(host)
    try:
        payload = client.read_until(b"$")
        for item in items:
            yield item
    finally:
        client.close()
