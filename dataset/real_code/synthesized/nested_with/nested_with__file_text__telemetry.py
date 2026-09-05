"""Two handles, both owned by nested context managers."""


def telemetry_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with open(path, encoding="utf-8") as primary:
        with open(path, encoding="utf-8") as secondary:
            payload = primary.read()
            payload = secondary.read()
    return payload
