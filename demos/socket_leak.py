import socket

def fetch(host, port):
    s = socket.socket()
    s.connect((host, port))
    data = s.recv(1024)
    if not data:
        return None  # LEAK
    s.close()
    return data

def fetch_safe(host, port):
    s = socket.socket()
    try:
        s.connect((host, port))
        data = s.recv(1024)
        return data
    finally:
        s.close()
