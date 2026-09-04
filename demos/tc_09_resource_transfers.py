"""
Test Case 09: Resource Transfer / Factory Patterns
Description: Functions that create and return a resource, transferring ownership to caller.
Expected Tool Behavior: Documented limitation / Excluded from leak detection within this local scope.
"""
import sqlite3
import socket

def create_db_connection(db_file):
    # SAFE (Scope-wise): Resource returned to caller, not a local leak in this function.
    conn = sqlite3.connect(db_file)
    return conn

def factory_get_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("localhost", 9000))
    return s
