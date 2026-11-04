from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class AppSettings:
    groq_api_key: str
    groq_model: str = "openai/gpt-oss-20b"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    chunk_size: int = 900
    chunk_overlap: int = 150
    top_k: int = 8
    max_iterations: int = 1
    validation_threshold: float = 0.65
    data_dir: str = "data"
    index_dir: str = "data/index"


def load_settings() -> AppSettings:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    return AppSettings(
        groq_api_key=api_key,
        groq_model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        embedding_model=os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ),
        reranker_model=os.getenv(
            "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
        ),
        chunk_size=int(os.getenv("CHUNK_SIZE", "900")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "150")),
        top_k=int(os.getenv("TOP_K", "8")),
        max_iterations=int(os.getenv("MAX_ITERATIONS", "1")),
        validation_threshold=float(os.getenv("VALIDATION_THRESHOLD", "0.65")),
        data_dir=os.getenv("DATA_DIR", "data"),
        index_dir=os.getenv("INDEX_DIR", "data/index"),
    )
