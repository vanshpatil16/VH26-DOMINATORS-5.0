def safe(path):
    f = open(path)
    data = f.read()
    if not data:
        f.close()
        return None
    f.close()
    return data
