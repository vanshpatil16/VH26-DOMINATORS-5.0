"""Two independent handles, each released in its own finally."""

import concurrent.futures


def telemetry_process_pool_exec(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = concurrent.futures.ProcessPoolExecutor(max_workers=2)
    try:
        target = concurrent.futures.ProcessPoolExecutor(max_workers=2)
        try:
            payload = list(source.map(worker, items))
            payload = list(target.map(worker, items))
        finally:
            target.shutdown()
    finally:
        source.shutdown()
    return payload
