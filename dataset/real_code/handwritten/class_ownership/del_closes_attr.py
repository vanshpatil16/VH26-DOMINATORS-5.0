"""Cleanup in __del__: fragile, but it is a closer and we recognise it."""

import sqlite3


class Cache:
    def __init__(self, path):
        self.db = sqlite3.connect(path)

    def get(self, key):
        return self.db.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()

    def __del__(self):
        self.db.close()
