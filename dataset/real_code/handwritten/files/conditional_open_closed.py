"""Both branches of the ternary bind the same handle, which is then closed."""


def read_either(primary, fallback, use_primary):
    handle = open(primary) if use_primary else open(fallback)
    try:
        return handle.read()
    finally:
        handle.close()
