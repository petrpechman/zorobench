import threading

from abc import ABC, abstractmethod
from functools import wraps
from typing import Optional

class BaseThreadItem(ABC):
    def __init__(self, queue: "BaseThreadQueue"):
        super().__init__()
        self.queue = queue

    @abstractmethod
    def __enter__(self) -> Optional["BaseThreadItem"]:
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_value, traceback):
        pass

    @abstractmethod
    def get_kwargs(self) -> dict:
        pass

class BaseThreadQueue(ABC):
    def __init__(self):
        super().__init__()
        self._lock = threading.RLock()

    @abstractmethod
    def get_item(self) -> BaseThreadItem | None:
        pass

def synchronized(method):
    @wraps(method)
    def _impl(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return _impl