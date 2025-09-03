import os
import asyncio

from ..requester.requester_worker import RequesterWorker
from ..requester.request_statistics import RequestStatistics
from ..threading_utils.threadpool import ThreadPool
from ..threading_utils.session_queue import SessionIDQueue
from ..data_utils.data_loader import DataLoader
from ..async_utils.asyncpool import AsyncPool
from ..async_utils.async_session_queue import AsyncSessionIDQueue
from ..requester.openai_api_requester import OpenAIAPIRequester

class Root:
    """
    TODO: Write
    """

    def run(self, 
            model: str, 
            filepath: str,
            concurrency: int = 1, 
            # stream: bool = False,
            use_multithreading: bool = False):
        """TODO: Write

        Args:
            num: Number.
        """
        api_key = os.getenv("SASANKA_TOKEN")
        base_url = "https://llm-proxy.seznam.net/v1"

        loader = DataLoader(filepath)
        request_payloads = loader.get_request_payloads()
        stream = True

        if use_multithreading:
            pool = ThreadPool(concurrency)

            requester_worker = RequesterWorker(stream, model, api_key, base_url)
            session_id_queue = SessionIDQueue(request_payloads)

            results: list[RequestStatistics] = pool.run(requester_worker, session_id_queue)
        else:
            pool = AsyncPool(concurrency)

            async_session_queue = AsyncSessionIDQueue(request_payloads)
            requester = OpenAIAPIRequester(stream=stream, model=model, api_key=api_key, base_url=base_url)

            results: list[RequestStatistics] = asyncio.run(pool.run(requester.send_request, async_session_queue))

        RequestStatistics.print(results)
        if use_multithreading:
            print("MULTITHREADING")
        else:
            print("ASYNC")
