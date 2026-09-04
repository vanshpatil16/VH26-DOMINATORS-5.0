"""Both the connection and the cursor are released."""

import contextlib
import sqlite3


def fetch_names(path):
    with contextlib.closing(sqlite3.connect(path)) as connection:
        with contextlib.closing(connection.cursor()) as cursor:
            cursor.execute("SELECT name FROM people")
            return [row[0] for row in cursor.fetchall()]
