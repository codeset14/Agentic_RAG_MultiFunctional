from __future__ import annotations

from functools import lru_cache
from typing import Any


@lru_cache(maxsize=4)
def cached_resource(key: str, builder: Any) -> Any:
    return builder()
