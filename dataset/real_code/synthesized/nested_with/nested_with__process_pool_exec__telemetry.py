"""Two handles, both owned by nested context managers."""

import concurrent.futures


def telemetry_process_pool_exec(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as primary:
        with concurrent.futures.ProcessPoolExecutor(max_workers=2) as secondary:
            payload = list(primary.map(worker, items))
            payload = list(secondary.map(worker, items))
    return payload
