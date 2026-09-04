"""An owner object usable as a context manager."""

import concurrent.futures


class BillingThreadPoolSession:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.pool.shutdown()

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        payload = list(self.pool.map(worker, items))
        return payload
