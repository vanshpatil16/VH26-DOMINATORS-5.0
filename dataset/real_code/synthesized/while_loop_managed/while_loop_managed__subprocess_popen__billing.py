"""One handle per iteration of a while loop, each released."""

import subprocess


def billing_subprocess_popen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    remaining = list(items)
    while remaining:
        remaining.pop()
        with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
            payload = process.stdout.read()
            collected.append(payload)
    return collected
