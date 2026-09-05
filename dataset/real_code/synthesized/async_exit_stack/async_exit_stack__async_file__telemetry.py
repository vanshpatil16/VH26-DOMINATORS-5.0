"""Load payload with an AsyncExitStack owning the handle."""

import aiofiles
import contextlib


async def telemetry_async_file(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    async with contextlib.AsyncExitStack() as stack:
        handle = await stack.enter_async_context(aiofiles.open(path, mode="r"))
        payload = await handle.read()
        return payload
