from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List


class ConversationMemory:
    def __init__(self, max_turns: int = 8) -> None:
        self._turns: Deque[Dict[str, str]] = deque(maxlen=max_turns)

    def add(self, role: str, content: str) -> None:
        self._turns.append({"role": role, "content": content})

    def to_messages(self) -> List[Dict[str, str]]:
        return list(self._turns)

    def clear(self) -> None:
        self._turns.clear()
