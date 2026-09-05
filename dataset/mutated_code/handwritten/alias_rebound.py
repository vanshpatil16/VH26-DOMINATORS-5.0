def process_log(path: str) -> str:
    f = open(path, "r")
    g = f
    f = open("/tmp/fallback.log", "r")
    data = f.read()
    f.close()
    return data
