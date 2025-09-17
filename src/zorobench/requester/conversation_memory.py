from collections import defaultdict
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall


class ConversationMemory:
    def __init__(self, limit_history: int | None = None):
        self._sessions: dict[str, list[dict[str, str]]] = defaultdict(list)
        self.max_history = limit_history

    def add_messages(self, session_id: str, messages: list[dict[str, str]]) -> None:
        self._sessions[session_id].extend(messages)
        self._truncate_if_needed(session_id)

    def add_assistant_message(self, session_id: str, content: str) -> None:
        self._sessions[session_id].append({"role": "assistant", "content": content})
        self._truncate_if_needed(session_id)

    def add_tool_call(self, session_id: str, tool_calls: dict[ChoiceDeltaToolCall]) -> None:
        tool_history = {"role": "assistant", "tool_calls": []}
        for _, tool_call in tool_calls.items():
            if tool_call.type != "function":
                raise Exception("No tool call is supported except for function calls.")
            tool_history["tool_calls"].append(tool_call.model_dump())
        self._sessions[session_id].append(tool_history)
        self._truncate_if_needed(session_id)

    def get_history(self, session_id: str) -> list[dict[str, str]]:
        return self._sessions[session_id]

    def clear(self, session_id: str) -> None:
        self._sessions[session_id] = []

    def _truncate_if_needed(self, session_id: str) -> None:
        if self.max_history is not None:
            self._sessions[session_id] = self._sessions[session_id][-self.max_history :]
