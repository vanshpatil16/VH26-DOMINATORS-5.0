def factory(path):
    f = open(path)
    return f  # ownership transferred -> not leak per config
