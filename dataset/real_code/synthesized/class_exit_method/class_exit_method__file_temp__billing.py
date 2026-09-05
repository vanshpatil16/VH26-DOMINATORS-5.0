"""An owner object usable as a context manager."""

import tempfile


class BillingFileTempSession:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        self.handle = tempfile.NamedTemporaryFile(delete=False)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.handle.close()

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        self.handle.write(payload)
        return payload
