from contextlib import ExitStack

def process_batch(paths):
    with ExitStack() as stack:
        f = open(paths[0], "r")
        data = f.read()
        return data
