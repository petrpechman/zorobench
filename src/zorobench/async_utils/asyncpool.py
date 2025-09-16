import asyncio

from typing import Callable, Any
from .async_session_queue import AsyncSessionIDQueue


class AsyncPool:
    def __init__(self, concurrency: int):
        self.concurrency = concurrency

    async def run(self, func: Callable[..., Any], async_session_queue: AsyncSessionIDQueue) -> list[Any]:
        results_queue: asyncio.Queue = asyncio.Queue()

        async def worker():
            while True:
                async with await async_session_queue.get_item() as ctx:
                    if ctx is None:
                        break
                    kwargs = ctx.get_kwargs()

                    if asyncio.iscoroutinefunction(func):
                        result = await func(**kwargs)
                    else:
                        result = func(**kwargs)
                    await results_queue.put(result)

        tasks = [asyncio.create_task(worker()) for _ in range(self.concurrency)]

        await asyncio.gather(*tasks)

        results = []
        while not results_queue.empty():
            results.append(results_queue.get_nowait())

        return results
