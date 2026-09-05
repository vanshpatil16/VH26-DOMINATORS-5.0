"""Load payload through contextlib.closing."""

import contextlib
import telnetlib


def telemetry_telnet(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.closing(telnetlib.Telnet(host)) as client:
        payload = client.read_until(b"$")
    return payload
