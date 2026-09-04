"""
Test Case 05: Complex Multi-Resource Cleanups
Description: Functions opening multiple resources where one is closed but another leaks.
"""
import sqlite3

def export_users_to_file(db_path, output_path):
    # Resource 1 opened
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Resource 2 opened
    out_file = open(output_path, "w")
    
    cursor.execute("SELECT username, email FROM users")
    for user in cursor.fetchall():
        out_file.write(f"{user[0]},{user[1]}\n")
        
    out_file.close()
    # LEAK: conn is never closed! (Partial resource leak)
