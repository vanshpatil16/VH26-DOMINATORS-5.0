"""One handle per iteration of a while loop, each released."""

import telnetlib


def ingest_telnet(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    remaining = list(items)
    while remaining:
        remaining.pop()
        with telnetlib.Telnet(host) as client:
            payload = client.read_until(b"$")
            collected.append(payload)
    return collected
