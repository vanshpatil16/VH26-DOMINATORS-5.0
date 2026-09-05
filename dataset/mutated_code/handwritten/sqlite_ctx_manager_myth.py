import sqlite3

def run_query(db_path: str):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        return cursor.fetchall()
