def foo(path):
    f = open(path)
    try:
        data = f.read()
        return data
    finally:
        f.close()
