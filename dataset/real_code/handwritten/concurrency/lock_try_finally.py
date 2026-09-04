"""Explicit acquire with a matching release in finally."""

import threading

LOCK = threading.Lock()


def guarded(action):
    LOCK.acquire()
    try:
        return action()
    finally:
        LOCK.release()
