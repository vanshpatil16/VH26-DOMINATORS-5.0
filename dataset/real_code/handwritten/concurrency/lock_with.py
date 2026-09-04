"""A counter guarded by a lock."""

import threading


class Counter:
    def __init__(self):
        self._lock = threading.Lock()
        self._value = 0

    def increment(self):
        with self._lock:
            self._value += 1
            return self._value
