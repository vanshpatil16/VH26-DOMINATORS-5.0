"""An owner object usable as a context manager."""

import telnetlib


class TelemetryTelnetSession:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        self.client = telnetlib.Telnet(host)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.client.close()

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        payload = self.client.read_until(b"$")
        return payload
