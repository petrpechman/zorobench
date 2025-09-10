import threading
from collections import defaultdict
from typing import List, Dict, Optional
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall, ChoiceDeltaToolCallFunction

class ConversationMemory:
    def __init__(self, limit_history: Optional[int] = None):
        """
        max_history: pokud je nastaveno, uchovává se pouze posledních N zpráv
        """
        self._sessions: dict[str, List[Dict[str, str]]] = defaultdict(list)
        self.max_history = limit_history

    def add_messages(self, session_id: str, messages: List[Dict[str, str]]) -> None:
        """Přidá zprávy do historie dané session."""
        self._sessions[session_id].extend(messages)
        self._truncate_if_needed(session_id)

    def add_assistant_message(self, session_id: str, content: str) -> None:
        """Přidá odpověď asistenta do historie."""
        self._sessions[session_id].append({"role": "assistant", "content": content})
        self._truncate_if_needed(session_id)
    
    def add_tool_call(self, session_id: str, tool_calls: dict[ChoiceDeltaToolCall]) -> None:
        tool_history = {
                "role": "assistant",
                "tool_calls": []
            }
        for index, tool_call in tool_calls.items():
            if tool_call.type != "function":
                raise Exception("No tool call is supported except for function calls.")
            tool_history["tool_calls"].append(tool_call.model_dump())
        self._sessions[session_id].append(tool_history)
        self._truncate_if_needed(session_id)

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """Vrátí historii konverzace."""
        return self._sessions[session_id]

    def clear(self, session_id: str) -> None:
        """Vymaže historii konkrétní session."""
        self._sessions[session_id] = []

    def _truncate_if_needed(self, session_id: str) -> None:
        """Pokud je nastaven max_history, ořeže historii."""
        if self.max_history is not None:
            self._sessions[session_id] = self._sessions[session_id][-self.max_history:]
