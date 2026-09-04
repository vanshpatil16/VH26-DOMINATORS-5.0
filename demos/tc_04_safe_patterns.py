"""
Test Case 04: Compliant Code (Safe Scopes)
Description: Proper resource management using context managers ('with') and 'try...finally'.
Expected Result: NO LEAKS FLAGGED
"""
import sqlite3
import socket

def safe_file_read(filepath):
    # SAFE: 'with' statement guarantees closure
    with open(filepath, "r") as f:
        return f.read()

def safe_db_transaction():
    # SAFE: Explicit try...finally block
    conn = sqlite3.connect("safe.db")
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE accounts SET balance = balance + 100")
        conn.commit()
    finally:
        conn.close()

def safe_socket_with():
    # SAFE: socket context manager
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("localhost", 8000))
        s.sendall(b"HELLO")
