"""Load payload asynchronously, awaiting the close in a finally."""

import aiofiles


async def ingest_async_file(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    handle = aiofiles.open(path, mode="r")
    try:
        payload = await handle.read()
        return payload
    finally:
        await handle.close()
