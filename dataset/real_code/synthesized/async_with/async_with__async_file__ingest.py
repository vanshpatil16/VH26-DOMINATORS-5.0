"""Load payload with an async context manager."""

import aiofiles


async def ingest_async_file(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    async with aiofiles.open(path, mode="r") as handle:
        payload = await handle.read()
    return payload
