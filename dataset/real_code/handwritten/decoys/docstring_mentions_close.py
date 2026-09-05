"""Module whose prose talks about closing files."""


def load(path):
    """Read a file.

    Remember to call handle.close() when you are done, unless you use the
    with-statement below, which does it for you. Never write:

        handle = open(path)
        return handle.read()
    """
    with open(path, encoding="utf-8") as handle:
        return handle.read()
