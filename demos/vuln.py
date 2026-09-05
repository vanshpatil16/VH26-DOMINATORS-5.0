"""Demo: CodeGate should flag leak in read_file but not in safe variants."""

def read_file(path):
    with open(path) as f:
        data = f.read()

        if not data:
            return None   # LEAK
    return data


def safe_with(path):
    with open(path) as f:
        data = f.read()
    return data


def safe_try_finally(path):
    f = open(path)
    try:
        data = f.read()
        return data
    finally:
        f.close()


def alias_safe(path):
    f = open(path)
    g = f
    g.close()
    return 1
