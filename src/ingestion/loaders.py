from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import List, Tuple

import pypdf

from src.utils.text import clean_text


def load_txt(file_bytes: bytes, filename: str) -> List[Tuple[str, int]]:
    text = file_bytes.decode("utf-8", errors="ignore")
    return [(clean_text(text), 1)]


def load_csv(file_bytes: bytes, filename: str) -> List[Tuple[str, int]]:
    data = file_bytes.decode("utf-8", errors="ignore")
    rows = []
    reader = csv.reader(io.StringIO(data))
    for i, row in enumerate(reader, start=1):
        rows.append((" | ".join(row), i))
    return [(clean_text("\n".join(r[0] for r in rows)), 1)]


def load_pdf(file_bytes: bytes, filename: str) -> List[Tuple[str, int]]:
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    pages: List[Tuple[str, int]] = []
    for i, page in enumerate(reader.pages, start=1):
        pages.append((clean_text(page.extract_text() or ""), i))
    return pages


def load_document(file_bytes: bytes, filename: str) -> List[Tuple[str, int]]:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return load_pdf(file_bytes, filename)
    if ext == ".txt":
        return load_txt(file_bytes, filename)
    if ext == ".csv":
        return load_csv(file_bytes, filename)
    raise ValueError(f"Unsupported file type: {ext}")
