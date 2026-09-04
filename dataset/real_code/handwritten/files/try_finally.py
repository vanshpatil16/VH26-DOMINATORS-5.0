"""Parse a file, releasing the handle even when parsing explodes."""

import json


def load_json(path):
    handle = open(path, encoding="utf-8")
    try:
        return json.load(handle)
    finally:
        handle.close()
