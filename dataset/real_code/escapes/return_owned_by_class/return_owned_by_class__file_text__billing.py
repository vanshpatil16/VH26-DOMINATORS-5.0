"""Factory output adopted by a class that closes it."""


def _acquire_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = open(path, encoding="utf-8")
    return handle


class BillingFileTextOwner:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.handle = _acquire_file_text(path, host, port)

    def billing_file_text(self):
        payload = self.handle.read()
        return payload

    def close(self):
        self.handle.close()
