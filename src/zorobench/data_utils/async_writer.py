import asyncio
import aiofiles
import os


class AsyncFileWriter:
    def __init__(self, filename: str):
        self.filename = filename
        if os.path.exists(self.filename):
            os.remove(self.filename)
        self.lock = asyncio.Lock()

    async def write(self, text: str):
        async with self.lock:
            async with aiofiles.open(self.filename, mode="a", encoding="utf-8") as f:
                await f.write(text + "\n")
