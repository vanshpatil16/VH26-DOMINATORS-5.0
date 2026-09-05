"""Wrap a raw descriptor; closing the wrapper closes the descriptor."""

import os
import tempfile


def write_temp(payload):
    fd, path = tempfile.mkstemp()
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(payload)
    return path
