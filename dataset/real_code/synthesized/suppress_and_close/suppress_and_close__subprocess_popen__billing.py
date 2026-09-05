"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import subprocess


def billing_subprocess_popen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    try:
        with contextlib.suppress(OSError):
            payload = process.stdout.read()
    finally:
        process.wait()
    return payload
