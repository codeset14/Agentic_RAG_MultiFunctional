from __future__ import annotations

from typing import List, Dict

from groq import AsyncGroq


class GroqClient:
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("GROQ_API_KEY is required.")
        self._client = AsyncGroq(api_key=api_key, timeout=30.0, max_retries=0)
        self.model = model

    async def complete(
        self, messages: List[Dict[str, str]], temperature: float = 0.1, max_tokens: int = 900
    ) -> str:
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (response.choices[0].message.content or "").strip()
