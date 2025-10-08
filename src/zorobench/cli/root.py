import asyncio
import logging
import time

from ..requester.request_statistics import RequestStatistics
from ..data_utils.data_loader import DataLoader
from ..async_utils.asyncpool import AsyncPool
from ..async_utils.async_session_queue import AsyncSessionIDQueue
from ..requester.openai_api_requester import OpenAIAPIRequester


class Root:
    """
    TODO: Write
    """

    def run(
        self,
        model: str,
        filepath: str,
        concurrency: int = 1,
        stream: bool = True,
        output_file: str = "output.json",
        log_responses: bool = False,
        verbose: bool = False,
    ):
        """
        Executes requests to the specified model using data from a file
        and collects statistics about each request.

        Args:
            model (str): Name of the model to benchmark.
            filepath (str): Path to the input file containing requests.
            concurrency (int, optional): Number of concurrent requests. Defaults to 1.
            stream (bool, optional): Whether to stream responses from the model. Defaults to True.
            output_file (str, optional): Path to the JSON file to save benchmark results. Defaults to "output.json".
            verbose (bool, optional): If True, enables detailed logging for progress and timing. Defaults to False.
        """

        log_level = logging.INFO if verbose else logging.WARN
        logging.basicConfig(
            level=log_level,
            format="[%(asctime)s] [%(levelname)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        loader = DataLoader(filepath)
        request_payloads = loader.get_request_payloads()
        stream = True

        pool = AsyncPool(concurrency)

        async_session_queue = AsyncSessionIDQueue(request_payloads)
        requester = OpenAIAPIRequester(stream=stream, model=model, log_responses=log_responses)

        now = time.perf_counter()
        stats: list[RequestStatistics] = asyncio.run(pool.run(requester.asend_request, async_session_queue))
        end = time.perf_counter()

        results = []
        count_errors = 0
        count_response_errors = 0
        count_runtime_errors = 0
        for stat in stats:
            if stat.status_code == 200:
                results.append(stat)
            elif stat.status_code == 600:
                count_runtime_errors += 1
                count_errors += 1
            else:
                count_response_errors += 1
                count_errors += 1

        logging.info("Successful requests: %d/%d", len(stats) - count_errors, len(stats))
        logging.info("Response errors: %d", count_response_errors)
        logging.info("Runtime errors: %d", count_runtime_errors)

        RequestStatistics.print(results)
        RequestStatistics.save_to_json(results, output_file)
        total_time = end - now
        logging.info(f"Total time: {total_time:.4f}")
