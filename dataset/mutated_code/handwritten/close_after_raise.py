import io

def parse_header(path: str):
    f = open(path, "rb")
    try:
        magic = f.read(4)
        if magic != b"LEAK":
            raise ValueError("bad magic")
        f.close()
    except ValueError:
        return None
