import subprocess

def launch_service():
    p = subprocess.Popen(["ls", "-la"])
    return "started"
