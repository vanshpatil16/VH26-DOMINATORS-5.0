"""Bound concurrent work with a semaphore."""

import threading


def limited(work, items, limit=4):
    gate = threading.Semaphore(limit)
    results = []
    for item in items:
        with gate:
            results.append(work(item))
    return results
