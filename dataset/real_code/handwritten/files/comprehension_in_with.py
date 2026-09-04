"""The comprehension runs inside the with-block, so the file is still owned."""


def head(path, limit=10):
    with open(path, encoding="utf-8") as handle:
        return [line for _index, line in zip(range(limit), handle)]
