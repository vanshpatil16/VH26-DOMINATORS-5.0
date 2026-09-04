"""
Test Case 03: Exceptions Bypassing Cleanup
Description: Operations between resource creation and close() may raise exceptions.
"""
import socket
import json

def send_payload(data):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("api.service.internal", 9000))
    
    # LEAK: json.dumps or sendall might raise an exception (e.g. TypeError, BrokenPipeError)
    # causing s.close() to be skipped completely.
    serialized = json.dumps(data)
    s.sendall(serialized.encode("utf-8"))
    
    s.close()

def query_database_unsafe(query):
    import sqlite3
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    # LEAK: Database error will raise sqlite3.Error before conn.close()
    cursor.execute(query)
    results = cursor.fetchall()
    
    conn.close()
    return results
