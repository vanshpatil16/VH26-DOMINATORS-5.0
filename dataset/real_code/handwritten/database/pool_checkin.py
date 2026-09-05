"""A pooled connection is checked back in rather than closed."""

import contextlib


class Pool:
    def __init__(self, factory):
        self._factory = factory
        self._idle = []

    @contextlib.contextmanager
    def lease(self):
        connection = self._idle.pop() if self._idle else self._factory()
        try:
            yield connection
        finally:
            self._idle.append(connection)


def run_query(pool, sql):
    with pool.lease() as connection:
        return connection.execute(sql).fetchall()
