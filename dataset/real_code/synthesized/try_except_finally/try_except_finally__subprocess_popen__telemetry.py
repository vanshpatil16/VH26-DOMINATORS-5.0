"""Load payload, logging failures but always releasing."""

import logging
import subprocess


def telemetry_subprocess_popen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    try:
        payload = process.stdout.read()
    except OSError:
        logging.warning("telemetry_subprocess_popen failed")
        payload = None
    finally:
        process.wait()
    return payload
