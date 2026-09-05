"""Load payload, logging failures but always releasing."""

import logging
import telnetlib


def telemetry_telnet(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = telnetlib.Telnet(host)
    try:
        payload = client.read_until(b"$")
    except OSError:
        logging.warning("telemetry_telnet failed")
        payload = None
    finally:
        client.close()
    return payload
