"""
Test Case 01: Simple Resource Leaks
Description: Standard function calls that open resources and fail to close them on normal execution paths.
"""
import sqlite3
import socket

def leak_db_connection():
    # LEAK: Database connection opened and never closed
    conn = sqlite3.connect("production.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()

def leak_raw_socket():
    # LEAK: Raw socket initialized and connected, but never closed
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", 8080))
    s.sendall(b"PING")
    data = s.recv(1024)
    return data

def leak_file_handle():
    # LEAK: File opened without context manager or close()
    f = open("audit.log", "a")
    f.write("System event triggered\n")
    # Missing f.close()
