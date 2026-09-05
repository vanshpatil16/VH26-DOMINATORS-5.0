"""An asyncio stream pair closed on every path."""

import asyncio


async def ping(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(b"ping")
        await writer.drain()
        return await reader.read(64)
    finally:
        writer.close()
        await writer.wait_closed()
