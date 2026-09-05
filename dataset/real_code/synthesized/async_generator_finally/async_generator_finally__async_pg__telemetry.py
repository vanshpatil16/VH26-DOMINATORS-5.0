"""An async generator whose finally awaits the close."""

import asyncpg


async def telemetry_async_pg(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = asyncpg.connect(dsn)
    try:
        payload = await connection.fetch("SELECT 1")
        for item in items:
            yield item
    finally:
        await connection.close()
