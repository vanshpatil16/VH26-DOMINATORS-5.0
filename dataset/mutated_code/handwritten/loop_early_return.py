import socket

def ping_servers(hosts):
    for host in hosts:
        s = socket.create_connection((host, 80))
        resp = s.recv(1024)
        if b"ERROR" in resp:
            return False  # leaks s
        s.close()
    return True
