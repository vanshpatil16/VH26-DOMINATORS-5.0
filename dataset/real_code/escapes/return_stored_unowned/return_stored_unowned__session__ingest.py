"""Factory return stored on a class that never releases it."""

import requests


def _acquire_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    session = requests.Session()
    return session


class IngestSessionHolder:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.session = _acquire_session(path, host, port)

    def ingest_session(self):
        payload = self.session.get(url)
        return payload
