import time


class RequestTimer:
    def __init__(self) -> None:
        self.start_time: float = 0.0
        self.first_token_time: float | None = None
        self.last_token_time: float | None = None
        self.itl_list: list[float] = []

    def start(self) -> None:
        """Start measuring the request."""
        self.start_time = time.perf_counter()

    def mark_token(self) -> None:
        """Mark arrival of a new token (chunk)."""
        now = time.perf_counter()
        if self.first_token_time is None:
            self.first_token_time = now
            self.last_token_time = now
        else:
            if self.last_token_time is None:
                raise RuntimeError("mark_token() called before first token")
            self.itl_list.append(now - self.last_token_time)
            self.last_token_time = now

    def finalize(self) -> tuple[float, float | None, tuple[float] | None]:
        """Get final metrics."""
        end_time = self.last_token_time or time.perf_counter()
        e2e = end_time - self.start_time
        ttft = None
        if self.first_token_time:
            ttft = self.first_token_time - self.start_time

        itl_list = tuple(self.itl_list) if self.itl_list else None

        self._clear()

        return e2e, ttft, itl_list

    def _clear(self):
        self.start_time = 0.0
        self.first_token_time = None
        self.last_token_time = None
        self.itl_list = []
