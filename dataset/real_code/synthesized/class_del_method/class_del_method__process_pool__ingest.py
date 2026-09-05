"""An owner object that releases its handle in __del__."""

import multiprocessing


class IngestProcessPoolOwner:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        self.pool = multiprocessing.Pool(processes=2)

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        payload = self.pool.map(worker, items)
        return payload

    def __del__(self):
        self.pool.close()
        self.pool.join()
