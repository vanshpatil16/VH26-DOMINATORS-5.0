"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import telnetlib


def telemetry_telnet(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = telnetlib.Telnet(host)
    try:
        with contextlib.suppress(OSError):
            payload = client.read_until(b"$")
    finally:
        client.close()
    return payload
