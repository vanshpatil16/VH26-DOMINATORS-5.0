"""Two independent handles, each released in its own finally."""

import subprocess


def billing_subprocess_popen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = subprocess.Popen(command, stdout=subprocess.PIPE)
    try:
        target = subprocess.Popen(command, stdout=subprocess.PIPE)
        try:
            payload = source.stdout.read()
            payload = target.stdout.read()
        finally:
            target.wait()
    finally:
        source.wait()
    return payload
