"""A worker whose pool is released by shutdown()."""

import concurrent.futures


class Worker:
    def __init__(self, size=4):
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=size)

    def submit(self, fn, *args):
        return self.pool.submit(fn, *args)

    def shutdown(self):
        self.pool.shutdown(wait=True)
