import sqlite3

class DatabaseWorker:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)

    def execute(self, query: str):
        return self.conn.execute(query).fetchall()
