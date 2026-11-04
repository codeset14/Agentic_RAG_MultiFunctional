from __future__ import annotations

from typing import List

from src.core.models import RetrievedChunk, RetrievalIteration
from src.embeddings.encoder import EmbeddingEncoder
from src.retrieval.faiss_store import FaissStore
from src.retrieval.keyword import KeywordRetriever
from src.retrieval.reranker import CrossEncoderReranker
from src.utils.text import naive_query_rewrite


class RetrieverAgent:
    def __init__(
        self,
        encoder: EmbeddingEncoder,
        faiss_store: FaissStore,
        keyword_retriever: KeywordRetriever,
        reranker: CrossEncoderReranker,
    ) -> None:
        self.encoder = encoder
        self.faiss = faiss_store
        self.keyword = keyword_retriever
        self.reranker = reranker

    def retrieve(self, query: str, iteration: int, top_k: int = 8) -> RetrievalIteration:
        query_vec = self.encoder.embed_texts([query])[0]
        semantic = self.faiss.search(query_vec, top_k=top_k * 2)
        sem_results = [
            RetrievedChunk(chunk=chunk, semantic_score=max(0.0, min(1.0, score)))
            for chunk, score in semantic
        ]

        kw_results = self.keyword.search(query, top_k=top_k * 2)

        merged = {}
        for result in sem_results + kw_results:
            cid = result.chunk.chunk_id
            if cid not in merged:
                merged[cid] = result
            else:
                merged[cid].semantic_score = max(
                    merged[cid].semantic_score, result.semantic_score
                )
                merged[cid].keyword_score = max(
                    merged[cid].keyword_score, result.keyword_score
                )
        candidates: List[RetrievedChunk] = list(merged.values())
        reranked = self.reranker.rerank(query, candidates, top_k=top_k)
        for item in reranked:
            item.combined_score = (
                0.45 * item.semantic_score + 0.2 * item.keyword_score + 0.35 * item.rerank_score
            )
        reranked.sort(key=lambda x: x.combined_score, reverse=True)
        return RetrievalIteration(
            iteration=iteration,
            query_used=query,
            chunks=reranked[:top_k],
            notes=f"Retrieved {len(reranked[:top_k])} chunks from hybrid search.",
        )

    def refine_query(self, query: str, feedback: str) -> str:
        return naive_query_rewrite(query, feedback)
