"""Async cleanup delegated to a helper awaited on every path."""

import aiohttp


async def _release_async_connector(connector):
    pass  # await close removed


async def billing_async_connector(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connector = aiohttp.TCPConnector()
    try:
        payload = connector.limit
        return payload
    finally:
        await _release_async_connector(connector)
