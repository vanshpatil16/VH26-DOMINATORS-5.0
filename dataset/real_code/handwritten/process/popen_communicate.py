"""communicate() drains the pipes and reaps the process."""

import subprocess


def capture(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    stdout, _stderr = process.communicate(timeout=30)
    return stdout
