from typing import Optional
from .thread_queue import BaseThreadQueue, BaseThreadItem, synchronized
from dataclasses import dataclass, field, asdict


@dataclass
class RequestPayload:
    messages: str
    session_id: str | None = None
    params: dict = field(default_factory=dict)


class SessionIDItem(BaseThreadItem):
    def __init__(self, queue: "SessionIDQueue", request_payload: RequestPayload | None, session_id: str | None):
        super().__init__(queue)
        self.request_payload = request_payload
        self.session_id = session_id
        self.active = False

    def __enter__(self) -> Optional["SessionIDItem"]:
        if self.request_payload is None:
            return None
        self.active = True
        return self
    
    def get_kwargs(self) -> dict:
        if not self.active:
            raise RuntimeError(f"SessionIDItem with session_id={self.session_id} is not active. Access only inside 'with' block.")
        return asdict(self.request_payload)
    
    def __exit__(self, exc_type, exc_value, traceback):
        if self.active:
            self.queue._session_end(self.session_id)
        self.active = False


class SessionIDQueue(BaseThreadQueue):
    def __init__(self, request_payloads: list[RequestPayload], session_id_key: str = "session_id"):
        super().__init__()
        self.request_payloads = request_payloads
        self.current_session_ids = set()
        self.session_id_key = session_id_key

    @synchronized
    def get_item(self) -> SessionIDItem | None:
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
        
        return SessionIDItem(self, return_request_payload, session_id)

    @synchronized
    def _session_end(self, session_id: str):
        self.current_session_ids.remove(session_id)
