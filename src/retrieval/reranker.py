from __future__ import annotations

from typing import List

from sentence_transformers import CrossEncoder

from src.core.models import RetrievedChunk


class CrossEncoderReranker:
    def __init__(self, model_name: str) -> None:
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, candidates: List[RetrievedChunk], top_k: int) -> List[RetrievedChunk]:
        if not candidates:
            return []
        pairs = [[query, c.chunk.text] for c in candidates]
        scores = self.model.predict(pairs).tolist()
        for c, score in zip(candidates, scores):
            c.rerank_score = float(score)
        ranked = sorted(candidates, key=lambda x: x.rerank_score, reverse=True)
        return ranked[:top_k]
