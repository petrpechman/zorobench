import threading
from queue import Queue
from typing import Callable, Any
from .thread_queue import BaseThreadQueue

class ThreadPool:
    def __init__(self, num_threads: int):
        self.num_threads = num_threads
        self.threads: list[threading.Thread] = []

    def run(self, func: Callable[..., None], session_queue: BaseThreadQueue) -> Any:
        results_queue = Queue()

        def worker():
            while True:
                with session_queue.get_item() as item_ctx:
                    if item_ctx is None:
                        break
                    kwargs = item_ctx.get_kwargs()
                    result = func(**kwargs)
                    results_queue.put(result)
                    

        self.threads = []
        for _ in range(self.num_threads):
            t = threading.Thread(target=worker)
            t.start()
            self.threads.append(t)

        for t in self.threads:
            t.join()

        results = []
        while not results_queue.empty():
            results.append(results_queue.get())

        return results
