"""Session object usable as a context manager."""

import requests


class ApiClient:
    def __init__(self, base):
        self.base = base
        self.session = requests.Session()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.session.close()

    def get(self, path):
        return self.session.get(self.base + path)
