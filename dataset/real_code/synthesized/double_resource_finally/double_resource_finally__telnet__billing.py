"""Two independent handles, each released in its own finally."""

import telnetlib


def billing_telnet(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = telnetlib.Telnet(host)
    try:
        target = telnetlib.Telnet(host)
        try:
            payload = source.read_until(b"$")
            payload = target.read_until(b"$")
        finally:
            target.close()
    finally:
        source.close()
    return payload
