"""An owner object usable as a context manager."""

import multiprocessing


class IngestProcessPoolSession:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        self.pool = multiprocessing.Pool(processes=2)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.pool.close()
        self.pool.join()

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        payload = self.pool.map(worker, items)
        return payload
