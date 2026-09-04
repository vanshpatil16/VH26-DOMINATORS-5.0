def foo(path):
    with open(path) as f:
        data = f.read()
    return data
