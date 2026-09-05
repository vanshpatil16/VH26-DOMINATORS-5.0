"""Load payload asynchronously, awaiting the close in a finally."""

import asyncpg


async def ingest_async_pg(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = asyncpg.connect(dsn)
    try:
        payload = await connection.fetch("SELECT 1")
        return payload
    finally:
        await connection.close()
