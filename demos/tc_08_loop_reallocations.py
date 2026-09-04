"""
Test Case 08: Resources Opened Inside Loops
Description: Opening new connections inside a loop without closing them inside the iteration.
"""
import sqlite3

def process_batch_databases(db_list):
    results = []
    for db_name in db_list:
        # LEAK: Each loop iteration overwrites 'conn', leaking previous connections!
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM logs")
        results.append(cursor.fetchone()[0])
        # Missing conn.close() inside loop body
    return results
