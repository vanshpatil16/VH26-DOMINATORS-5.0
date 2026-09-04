"""
Test Case 06: Conditional Cleanup Paths
Description: Resource closed in one branch of an if-else statement but missed in another.
"""
import sqlite3

def Sync_data(mode):
    conn = sqlite3.connect("sync.db")
    cursor = conn.cursor()
    
    if mode == "FAST":
        cursor.execute("PRAGMA synchronous = OFF")
        conn.close()  # Closed here
    elif mode == "FULL":
        cursor.execute("PRAGMA synchronous = FULL")
        # LEAK: Missed conn.close() in this branch!
    else:
        conn.close()  # Closed here
        
    return True
