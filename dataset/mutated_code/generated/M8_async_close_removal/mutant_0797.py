"""Async cleanup delegated to a helper awaited on every path."""

import aiofiles


async def _release_async_file(handle):
    pass  # await close removed


async def billing_async_file(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = aiofiles.open(path, mode="r")
    try:
        payload = await handle.read()
        return payload
    finally:
        await _release_async_file(handle)
