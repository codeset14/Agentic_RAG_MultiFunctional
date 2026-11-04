from __future__ import annotations

import re


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def naive_query_rewrite(query: str, feedback: str) -> str:
    if not feedback:
        return query
    return f"{query}. Focus on: {feedback[:160]}"
