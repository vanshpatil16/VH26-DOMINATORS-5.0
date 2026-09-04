"""A hand-rolled context manager whose cleanup follows the yield."""

import contextlib


@contextlib.contextmanager
def opened(path):
    handle = open(path, encoding="utf-8")
    try:
        yield handle
    finally:
        handle.close()
