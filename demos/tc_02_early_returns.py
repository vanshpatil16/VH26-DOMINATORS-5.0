"""
Test Case 02: Leaks via Early Return
Description: Resource is properly closed at the end of function, but early returns skip the cleanup.
"""
import sqlite3

def get_user_status(user_id):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT active FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row is None:
        # LEAK: Early return without closing connection
        return "NOT_FOUND"
        
    if not row[0]:
        # LEAK: Another early return missing close()
        return "INACTIVE"
        
    status = "ACTIVE"
    conn.close()  # Only reached if all conditionals pass
    return status
