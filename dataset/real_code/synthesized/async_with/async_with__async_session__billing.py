"""Load payload with an async context manager."""

import aiohttp


async def billing_async_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    async with aiohttp.ClientSession() as session:
        payload = await session.get(url)
    return payload
