from __future__ import annotations

import uuid
from typing import List, Tuple

from src.core.models import DocumentChunk


def chunk_text(
    pages: List[Tuple[str, int]],
    source: str,
    chunk_size: int = 900,
    chunk_overlap: int = 150,
) -> List[DocumentChunk]:
    chunks: List[DocumentChunk] = []
    for text, page_num in pages:
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            piece = text[start:end].strip()
            if piece:
                chunks.append(
                    DocumentChunk(
                        chunk_id=str(uuid.uuid4()),
                        source=source,
                        page=page_num,
                        text=piece,
                        metadata={"start": start, "end": end},
                    )
                )
            if end >= len(text):
                break
            start = max(0, end - chunk_overlap)
    return chunks
