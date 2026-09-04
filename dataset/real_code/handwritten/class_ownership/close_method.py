"""A client whose close() releases the socket it owns."""

import socket


class Client:
    def __init__(self, host, port):
        self.sock = socket.create_connection((host, port))

    def send(self, payload):
        self.sock.sendall(payload)

    def close(self):
        self.sock.close()
