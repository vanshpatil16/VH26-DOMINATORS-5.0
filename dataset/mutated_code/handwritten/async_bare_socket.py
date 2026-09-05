import asyncio

async def fetch_data(host: str, port: int):
    reader, writer = await asyncio.open_connection(host, port)
    writer.write(b"GET / HTTP/1.0\r\n\r\n")
    await writer.drain()
    data = await reader.read(100)
    return data
