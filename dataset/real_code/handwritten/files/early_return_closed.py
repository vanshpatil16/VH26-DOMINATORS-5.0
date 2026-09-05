"""Early returns that each release the handle before leaving."""


def first_non_empty_line(path):
    handle = open(path, encoding="utf-8")
    try:
        for line in handle:
            if line.strip():
                return line.strip()
        return ""
    finally:
        handle.close()
