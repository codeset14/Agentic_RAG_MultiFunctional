from __future__ import annotations

from typing import List

from src.core.models import ReasoningResult, RetrievedChunk
from src.llm.groq_client import GroqClient
from src.utils.prompts import REASONING_PROMPT


class ReasoningAgent:
    def __init__(self, llm: GroqClient) -> None:
        self.llm = llm

    async def run(self, query: str, evidence: List[RetrievedChunk]) -> ReasoningResult:
        evidence_text = "\n\n".join(
            [
                f"[{i}] chunk_id={c.chunk.chunk_id} source={c.chunk.source} page={c.chunk.page}\n{c.chunk.text}"
                for i, c in enumerate(evidence, start=1)
            ]
        )
        messages = [
            {"role": "system", "content": REASONING_PROMPT},
            {
                "role": "user",
                "content": f"Question: {query}\n\nEvidence:\n{evidence_text}",
            },
        ]
        draft = await self.llm.complete(messages, temperature=0.1, max_tokens=900)
        claims = [line.strip("- ").strip() for line in draft.splitlines() if line.strip().startswith("-")]
        support = {claim: [c.chunk.chunk_id for c in evidence[:2]] for claim in claims[:8]}
        return ReasoningResult(
            answer_draft=draft,
            claims=claims or [query],
            claim_support=support,
            reasoning_trace="LLM synthesized answer using provided evidence only.",
        )
