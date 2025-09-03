import threading

from .openai_api_requester import OpenAIAPIRequester
from .conversation_memory import ConversationMemory

class RequesterWorker:
    def __init__(self, stream: bool, model: str, api_key: str | None = None, base_url: str | None = None):
        self.model = model
        self.stream = stream
        self.api_key = api_key
        self.base_url = base_url
        self.thread_local = threading.local()
        self.memory = ConversationMemory()

    def _get_requester(self):
        if not hasattr(self.thread_local, "requester"):
            self.thread_local.requester = OpenAIAPIRequester(
                model=self.model,
                stream=self.stream,
                api_key=self.api_key,
                base_url=self.base_url,
                memory=self.memory,
            )
        return self.thread_local.requester

    def __call__(self, **kwargs):
        requester = self._get_requester()
        return requester.send_request(**kwargs)
