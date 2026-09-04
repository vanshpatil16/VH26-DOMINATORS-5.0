"""An ExitStack that is closed explicitly rather than via with."""

import contextlib


def read_pair(first, second):
    stack = contextlib.ExitStack()
    try:
        left = stack.enter_context(open(first, encoding="utf-8"))
        right = stack.enter_context(open(second, encoding="utf-8"))
        return left.read(), right.read()
    finally:
        stack.close()
