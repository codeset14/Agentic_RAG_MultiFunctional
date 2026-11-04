from __future__ import annotations

import json
from typing import Dict

from src.core.models import AnalyzerResult
from src.llm.groq_client import GroqClient
from src.utils.prompts import QUERY_ANALYZER_PROMPT


class QueryAnalyzerAgent:
    def __init__(self, llm: GroqClient) -> None:
        self.llm = llm

    async def run(self, query: str, memory: list[Dict[str, str]]) -> AnalyzerResult:
        messages = [
            {"role": "system", "content": QUERY_ANALYZER_PROMPT},
            {
                "role": "user",
                "content": f"Conversation: {memory}\n\nUser query: {query}",
            },
        ]
        raw = await self.llm.complete(messages, temperature=0.0, max_tokens=400)
        try:
            data = json.loads(raw)
            return AnalyzerResult(
                intent=data.get("intent", "factual"),
                needs_multi_step=bool(data.get("needs_multi_step", False)),
                sub_questions=data.get("sub_questions", [])[:5],
                rewritten_query=data.get("rewritten_query", query),
                expected_evidence_count=int(data.get("expected_evidence_count", 3)),
                rationale=data.get("rationale", ""),
            )
        except Exception:
            return AnalyzerResult(
                intent="factual",
                needs_multi_step=(" and " in query.lower()) or ("compare" in query.lower()),
                sub_questions=[query],
                rewritten_query=query,
                expected_evidence_count=3,
                rationale="Fallback heuristic parser.",
            )
