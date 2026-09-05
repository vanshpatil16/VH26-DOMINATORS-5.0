"""One handle per item, each released inside the loop."""

import subprocess


def telemetry_subprocess_popen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
            payload = process.stdout.read()
            collected.append(payload)
    return collected
