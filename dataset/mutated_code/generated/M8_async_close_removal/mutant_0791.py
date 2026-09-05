"""An async generator whose finally awaits the close."""

import aiohttp


async def billing_async_connector(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connector = aiohttp.TCPConnector()
    try:
        payload = connector.limit
        for item in items:
            yield item
    finally:
        pass  # await close removed
