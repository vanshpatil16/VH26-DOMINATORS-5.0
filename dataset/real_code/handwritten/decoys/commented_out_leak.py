"""A previous, leaky implementation survives only as a comment."""


def read(path):
    # handle = open(path)
    # return handle.read()
    with open(path, encoding="utf-8") as handle:
        return handle.read()
