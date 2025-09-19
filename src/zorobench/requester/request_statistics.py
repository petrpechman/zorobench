import json
import numpy as np

from dataclasses import dataclass


@dataclass(frozen=True)
class RequestStatistics:
    e2e: float
    ttft: float | None
    itl: tuple[float] | None
    token_num: int | None
    status_code: int | None = None

    @staticmethod
    def _describe(values: list[float]) -> dict[str, float]:
        if not values:
            nan = float("nan")
            return {"mean": nan, "p50": nan, "p75": nan, "p95": nan, "p99": nan, "max": nan, "min": nan}
        arr = np.array(values)
        return {
            "mean": float(np.mean(arr)),
            "p50": float(np.percentile(arr, 50)),
            "p75": float(np.percentile(arr, 75)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "max": float(np.max(arr)),
            "min": float(np.min(arr)),
        }

    @staticmethod
    def _status_breakdown(statistics: list["RequestStatistics"]) -> dict[str, int]:
        status_breakdown: dict[str, int] = {}
        for s in statistics:
            key = str(s.status_code) if s.status_code is not None else "unknown"
            status_breakdown[key] = status_breakdown.get(key, 0) + 1
        return status_breakdown

    @staticmethod
    def _create_itl(e2e_values: list[float], ttft_values: list[float], token_nums: list[int]) -> list[float]:
        itl_values = []
        for e2e, ttft, token_num in zip(e2e_values, ttft_values, token_nums):
            itl = (e2e - ttft) / token_num
            itl_values.append(itl)
        return itl_values

    @staticmethod
    def print(statistics: list["RequestStatistics"]) -> None:
        e2e_values = [s.e2e for s in statistics]
        ttft_values = [s.ttft for s in statistics if s.ttft is not None]
        # itl_values = [t for s in statistics if s.itl for t in s.itl]
        token_nums = [s.token_num for s in statistics if s.token_num is not None]

        itl_values = RequestStatistics._create_itl(e2e_values, ttft_values, token_nums)

        print("E2E:", RequestStatistics._describe(e2e_values))
        print("TTFT:", RequestStatistics._describe(ttft_values))
        print("ITL:", RequestStatistics._describe(itl_values))
        print("Output tokens:", RequestStatistics._describe(token_nums))
        print("Status codes:", RequestStatistics._status_breakdown(statistics))

    @staticmethod
    def save_to_json(statistics: list["RequestStatistics"], filename: str) -> None:
        e2e_values = [s.e2e for s in statistics]
        ttft_values = [s.ttft for s in statistics if s.ttft is not None]
        # itl_values = [t for s in statistics if s.itl for t in s.itl]
        token_nums = [s.token_num for s in statistics if s.token_num is not None]
        status_breakdown = RequestStatistics._status_breakdown(statistics)

        itl_values = RequestStatistics._create_itl(e2e_values, ttft_values, token_nums)

        data = {
            "E2E": RequestStatistics._describe(e2e_values),
            "TTFT": RequestStatistics._describe(ttft_values),
            "ITL": RequestStatistics._describe(itl_values),
            "Output tokens": RequestStatistics._describe(token_nums),
            "Status codes": status_breakdown,
        }

        with open(filename, "w") as f:
            json.dump(data, f, indent=4, sort_keys=True)
