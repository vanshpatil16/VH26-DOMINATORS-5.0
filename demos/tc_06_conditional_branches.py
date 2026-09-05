"""
Test Case 06: Conditional Cleanup Paths
Description: Resource closed in one branch of an if-else statement but missed in another.
"""
import sqlite3

def Sync_data(mode):
    with sqlite3.connect("sync.db") as conn:
        cursor = conn.cursor()
    return True
