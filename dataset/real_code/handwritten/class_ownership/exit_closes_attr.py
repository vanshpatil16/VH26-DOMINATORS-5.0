"""The class owns the connection and releases it in __exit__."""

import sqlite3


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.db.close()

    def names(self):
        return [row[0] for row in self.db.execute("SELECT name FROM people")]
