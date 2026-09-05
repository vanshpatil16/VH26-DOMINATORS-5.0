"""Acquire, release, then acquire a second time and release again."""

import telnetlib


def telemetry_telnet(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = telnetlib.Telnet(host)
    try:
        payload = client.read_until(b"$")
    finally:
        client.close()
    retry = telnetlib.Telnet(host)
    try:
        payload = retry.read_until(b"$")
    finally:
        retry.close()
    return payload
