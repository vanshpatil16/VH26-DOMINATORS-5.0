"""Insert a row, releasing the connection on every path."""

import sqlite3


def insert(path, name):
    connection = sqlite3.connect(path)
    try:
        connection.execute("INSERT INTO people (name) VALUES (?)", (name,))
        connection.commit()
    finally:
        connection.close()
