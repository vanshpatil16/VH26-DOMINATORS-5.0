"""ExitStack registers cleanup for a variable number of files."""

import contextlib


def concat(paths):
    with contextlib.ExitStack() as stack:
        handles = [stack.enter_context(open(path, encoding="utf-8")) for path in paths]
        return "".join(handle.read() for handle in handles)
