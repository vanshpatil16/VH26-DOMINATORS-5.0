"""Copy one file to another using a single multi-item with."""


def copy(src, dst):
    with open(src, "rb") as source, open(dst, "wb") as target:
        target.write(source.read())
