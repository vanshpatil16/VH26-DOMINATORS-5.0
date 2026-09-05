"""One handle per item, released in a finally."""

import subprocess


def billing_subprocess_popen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        try:
            payload = process.stdout.read()
            collected.append(payload)
        finally:
            process.wait()
    return collected
