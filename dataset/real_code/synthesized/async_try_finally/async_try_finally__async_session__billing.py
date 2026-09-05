"""Load payload asynchronously, awaiting the close in a finally."""

import aiohttp


async def billing_async_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    session = aiohttp.ClientSession()
    try:
        payload = await session.get(url)
        return payload
    finally:
        await session.close()
