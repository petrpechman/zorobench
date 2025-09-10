from typing import Optional
from dataclasses import dataclass, field, asdict
import asyncio

@dataclass
class RequestPayload:
    messages: str
    session_id: str | None = None
    params: dict = field(default_factory=dict)


class AsyncIDItem:
    """Async context manager pro jeden item v queue."""
    def __init__(self, queue: "AsyncSessionIDQueue", request_payload: RequestPayload | None, session_id: str | None):
        self.queue = queue
        self.request_payload = request_payload
        self.session_id = session_id
        self.active = False

    async def __aenter__(self) -> Optional["AsyncIDItem"]:
        if self.request_payload is None:
            return None
        self.active = True
        return self

    def get_kwargs(self) -> dict:
        if not self.active:
            raise RuntimeError(f"SessionIDItem with session_id={self.session_id} is not active. Access only inside 'async with' block.")
        return asdict(self.request_payload)

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self.active:
            await self.queue._session_end(self.session_id)
        self.active = False


class AsyncSessionIDQueue:
    """Async verze SessionIDQueue."""
    def __init__(self, request_payloads: list[RequestPayload], session_id_key: str = "session_id"):
        self.request_payloads = request_payloads
        self.current_session_ids = set()
        self.session_id_key = session_id_key
        self._lock = asyncio.Lock()

    async def get_item(self) -> AsyncIDItem:
        async with self._lock:
            index = None
            session_id = None
            return_request_payload = None

            for i, request_payload in enumerate(self.request_payloads):
                if request_payload.session_id not in self.current_session_ids:
                    index = i
                    break

            if index is not None:
                return_request_payload = self.request_payloads.pop(index)
                session_id = return_request_payload.session_id
                self.current_session_ids.add(session_id)

            return AsyncIDItem(self, return_request_payload, session_id)

    async def _session_end(self, session_id: str):
        async with self._lock:
            self.current_session_ids.remove(session_id)
