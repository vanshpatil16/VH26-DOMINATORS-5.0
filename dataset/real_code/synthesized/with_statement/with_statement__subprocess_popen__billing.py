"""Load payload using a context manager."""

import subprocess


def billing_subprocess_popen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
        payload = process.stdout.read()
    return payload
