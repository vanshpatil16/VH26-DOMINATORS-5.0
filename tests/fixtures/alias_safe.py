def foo(path):
    f = open(path)
    g = f
    g.close()
    return 1
