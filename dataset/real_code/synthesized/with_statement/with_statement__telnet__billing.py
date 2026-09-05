"""Load payload using a context manager."""

import telnetlib


def billing_telnet(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with telnetlib.Telnet(host) as client:
        payload = client.read_until(b"$")
    return payload
