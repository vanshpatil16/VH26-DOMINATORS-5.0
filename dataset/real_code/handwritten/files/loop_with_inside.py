"""One handle per iteration, each closed by the with-block."""


def total_size(paths):
    total = 0
    for path in paths:
        with open(path, "rb") as handle:
            total += len(handle.read())
    return total
