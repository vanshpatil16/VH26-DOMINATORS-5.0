def leak(path):
    f = open(path)
    data = f.read()
    if not data:
        return None
    f.close()
    return data
