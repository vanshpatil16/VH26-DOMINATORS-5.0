"""An owner object that releases its handle in close()."""

import concurrent.futures


class BillingThreadPoolClient:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        payload = list(self.pool.map(worker, items))
        return payload

    def close(self):
        self.pool.shutdown()
