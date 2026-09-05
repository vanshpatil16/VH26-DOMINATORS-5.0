"""Two handles, both owned by nested context managers."""

import subprocess


def billing_subprocess_popen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with subprocess.Popen(command, stdout=subprocess.PIPE) as primary:
        with subprocess.Popen(command, stdout=subprocess.PIPE) as secondary:
            payload = primary.stdout.read()
            payload = secondary.stdout.read()
    return payload
