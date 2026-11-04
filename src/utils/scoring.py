from __future__ import annotations

from typing import List

from src.core.models import RetrievedChunk, ValidationResult


def retrieval_quality(chunks: List[RetrievedChunk]) -> float:
    if not chunks:
        return 0.0
    top_scores = [c.combined_score for c in chunks[:5]]
    return max(0.0, min(1.0, sum(top_scores) / max(len(top_scores), 1)))


def confidence_score(chunks: List[RetrievedChunk], validation: ValidationResult) -> float:
    rel = retrieval_quality(chunks)
    conf = 0.55 * rel + 0.45 * validation.confidence
    if not validation.is_valid:
        conf *= 0.7
    return max(0.0, min(1.0, conf))
