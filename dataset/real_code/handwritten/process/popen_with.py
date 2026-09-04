"""Popen as a context manager waits and closes the pipes."""

import subprocess


def run(command):
    with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
        return process.stdout.read()
