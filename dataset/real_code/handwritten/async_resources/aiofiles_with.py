"""Read a file without blocking the loop."""

import aiofiles


async def read_text(path):
    async with aiofiles.open(path, mode="r") as handle:
        return await handle.read()
