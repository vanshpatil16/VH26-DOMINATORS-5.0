"""Two handles, both owned by nested context managers."""

import telnetlib


def ingest_telnet(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with telnetlib.Telnet(host) as primary:
        with telnetlib.Telnet(host) as secondary:
            payload = primary.read_until(b"$")
            payload = secondary.read_until(b"$")
    return payload
