"""Load payload with an AsyncExitStack owning the handle."""

import aiohttp
import contextlib


async def ingest_async_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    async with contextlib.AsyncExitStack() as stack:
        session = await stack.enter_async_context(aiohttp.ClientSession())
        payload = await session.get(url)
        return payload
