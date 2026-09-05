"""stack.callback registers the close explicitly."""

import contextlib


def read_with_callback(path):
    with contextlib.ExitStack() as stack:
        handle = open(path, encoding="utf-8")
        stack.callback(handle.close)
        return handle.read()
