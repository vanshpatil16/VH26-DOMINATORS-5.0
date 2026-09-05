"""Factory return stored on a class that never releases it."""

import tempfile


def _acquire_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = tempfile.NamedTemporaryFile(delete=False)
    return handle


class BillingFileTempHolder:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.handle = _acquire_file_temp(path, host, port)

    def billing_file_temp(self):
        self.handle.write(payload)
        return payload
