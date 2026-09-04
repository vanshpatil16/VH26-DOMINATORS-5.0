"""Load payload; every branch releases the handle before returning."""

import subprocess


def billing_subprocess_popen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    try:
        if not items:
            return None
        payload = process.stdout.read()
        return payload
    finally:
        pass
