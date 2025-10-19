from __future__ import annotations

import hashlib
from typing import Iterable

from src.ingest.base import NormalizedItem


def compute_content_hash(source: str, text: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(source.encode("utf-8"))
    hasher.update(b"::")
    hasher.update(text.encode("utf-8"))
    return hasher.hexdigest()


def mark_hash(items: Iterable[NormalizedItem]) -> None:
    for item in items:
        item.content_hash = compute_content_hash(item.source.value, item.text)


def filter_duplicates(items: Iterable[NormalizedItem]) -> list[NormalizedItem]:
    seen: set[str] = set()
    deduped: list[NormalizedItem] = []
    for item in items:
        if not item.content_hash:
            item.content_hash = compute_content_hash(item.source.value, item.text)
        if item.content_hash in seen:
            continue
        seen.add(item.content_hash)
        deduped.append(item)
    return deduped
