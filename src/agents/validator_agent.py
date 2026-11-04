from __future__ import annotations

import json
from typing import List

from src.core.models import ReasoningResult, RetrievedChunk, ValidationResult
from src.llm.groq_client import GroqClient
from src.utils.prompts import VALIDATOR_PROMPT


class ValidatorAgent:
    def __init__(self, llm: GroqClient) -> None:
        self.llm = llm

    async def run(self, reasoning: ReasoningResult, evidence: List[RetrievedChunk]) -> ValidationResult:
        evidence_digest = [
            {"chunk_id": c.chunk.chunk_id, "source": c.chunk.source, "text": c.chunk.text[:350]}
            for c in evidence
        ]
        messages = [
            {"role": "system", "content": VALIDATOR_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "claims": reasoning.claims,
                        "answer_draft": reasoning.answer_draft,
                        "evidence": evidence_digest,
                    }
                ),
            },
        ]
        raw = await self.llm.complete(messages, temperature=0.0, max_tokens=500)
        try:
            data = json.loads(raw)
            return ValidationResult(
                is_valid=bool(data.get("is_valid", False)),
                unsupported_claims=data.get("unsupported_claims", []),
                contradictions=data.get("contradictions", []),
                confidence=float(data.get("confidence", 0.0)),
                feedback=data.get("feedback", ""),
            )
        except Exception:
            fallback_valid = len(reasoning.claims) <= max(len(evidence), 1) + 2
            return ValidationResult(
                is_valid=fallback_valid,
                unsupported_claims=[] if fallback_valid else reasoning.claims[:2],
                contradictions=[],
                confidence=0.55 if fallback_valid else 0.35,
                feedback="Fallback validator used due to parser failure.",
            )
