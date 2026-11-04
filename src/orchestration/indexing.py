from __future__ import annotations

from typing import Iterable, List, Tuple

from src.core.models import DocumentChunk
from src.embeddings.encoder import EmbeddingEncoder
from src.ingestion.chunker import chunk_text
from src.ingestion.loaders import load_document
from src.retrieval.faiss_store import FaissStore
from src.retrieval.keyword import KeywordRetriever


class IndexingService:
    def __init__(
        self,
        encoder: EmbeddingEncoder,
        faiss_store: FaissStore,
        keyword_retriever: KeywordRetriever,
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        self.encoder = encoder
        self.faiss = faiss_store
        self.keyword = keyword_retriever
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def build_from_uploads(self, uploads: Iterable[Tuple[str, bytes]]) -> List[DocumentChunk]:
        all_chunks: List[DocumentChunk] = []
        for filename, file_bytes in uploads:
            pages = load_document(file_bytes, filename)
            chunks = chunk_text(
                pages=pages,
                source=filename,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
            all_chunks.extend(chunks)

        if not all_chunks:
            raise ValueError("The uploaded documents did not contain searchable text.")

        vectors = self.encoder.embed_texts([c.text for c in all_chunks])
        self.faiss.append(all_chunks, vectors)
        self.faiss.save()
        self.keyword.fit(self.faiss.chunks)
        return all_chunks
