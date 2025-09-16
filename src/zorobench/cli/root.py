import asyncio
import logging
import time

from ..requester.request_statistics import RequestStatistics
from ..data_utils.data_loader import DataLoader
from ..async_utils.asyncpool import AsyncPool
from ..async_utils.async_session_queue import AsyncSessionIDQueue
from ..requester.openai_api_requester import OpenAIAPIRequester

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] [%(levelname)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)


class Root:
    """
    TODO: Write
    """

    def run(
        self,
        model: str,
        filepath: str,
        concurrency: int = 1,
        # stream: bool = False,
        output_file: str = "output.json",
    ):
        """TODO: Write

        Args:
            num: Number.
        """
        api_key = None
        base_url = None

        loader = DataLoader(filepath)
        request_payloads = loader.get_request_payloads()
        stream = True

        now = time.perf_counter()

        pool = AsyncPool(concurrency)

        async_session_queue = AsyncSessionIDQueue(request_payloads)
        requester = OpenAIAPIRequester(stream=stream, model=model, api_key=api_key, base_url=base_url)

        results: list[RequestStatistics] = asyncio.run(pool.run(requester.asend_request, async_session_queue))

        end = time.perf_counter()

        RequestStatistics.print(results)
        RequestStatistics.save_to_json(results, output_file)
        total_time = end - now
        logging.info(f"Total time: {total_time:.4f}")
