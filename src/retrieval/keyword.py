from __future__ import annotations

from typing import List

from rank_bm25 import BM25Okapi

from src.core.models import DocumentChunk, RetrievedChunk


class KeywordRetriever:
    def __init__(self) -> None:
        self._bm25: BM25Okapi | None = None
        self._chunks: List[DocumentChunk] = []

    def fit(self, chunks: List[DocumentChunk]) -> None:
        self._chunks = chunks
        corpus = [c.text.lower().split() for c in chunks]
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def search(self, query: str, top_k: int = 8) -> List[RetrievedChunk]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(query.lower().split())
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        max_score = max([scores[i] for i in order], default=1.0) or 1.0
        results: List[RetrievedChunk] = []
        for i in order:
            results.append(
                RetrievedChunk(
                    chunk=self._chunks[i],
                    semantic_score=0.0,
                    keyword_score=float(scores[i]) / max_score,
                )
            )
        return results
