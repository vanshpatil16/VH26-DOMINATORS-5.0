"""
Test Case 07: False Positive Traps (Tricky Valid Code)
Description: Code patterns designed to trick naive AST scanners or regex matchers into reporting false leaks.
Expected Result: NO LEAKS FLAGGED
"""
import sqlite3

def closed_in_helper_or_alias():
    conn = sqlite3.connect("test.db")
    db_alias = conn  # Reassignment / Alias
    
    try:
        cursor = db_alias.cursor()
        cursor.execute("SELECT 1")
    finally:
        db_alias.close()  # Closed via alias variable

def variable_shadowing_and_reopening():
    # Open and close properly twice
    f = open("file1.txt", "r")
    content1 = f.read()
    f.close()
    
    f = open("file2.txt", "r")
    content2 = f.read()
    f.close()
    
    return content1 + content2
