"""AsyncExitStack unwinds every registered async resource."""

import contextlib

import aiohttp


async def fetch_one(url):
    async with contextlib.AsyncExitStack() as stack:
        session = await stack.enter_async_context(aiohttp.ClientSession())
        response = await session.get(url)
        return await response.text()
