"""A process-lifetime log handle released by atexit."""

import atexit

AUDIT = open("audit.log", "a", encoding="utf-8")
atexit.register(AUDIT.close)


def record(message):
    AUDIT.write(message)
    AUDIT.flush()
