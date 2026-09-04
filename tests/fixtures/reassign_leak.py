def foo(path):
    f = open(path)
    f = open(path)  # leaks first
    f.close()
    return 1
