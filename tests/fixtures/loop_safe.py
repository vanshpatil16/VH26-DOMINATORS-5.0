def foo(path):
    f = open(path)
    for i in range(3):
        print(i)
    f.close()
    return 1
