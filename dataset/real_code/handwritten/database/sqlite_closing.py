"""`with sqlite3.connect(...)` is a TRANSACTION manager, so wrap it in closing."""

import contextlib
import sqlite3


def count_rows(path, table):
    with contextlib.closing(sqlite3.connect(path)) as connection:
        cursor = connection.execute("SELECT COUNT(*) FROM " + table)
        return cursor.fetchone()[0]
