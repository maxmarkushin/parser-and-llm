from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Item
from src.llm.client import LMStudioClient


@dataclass(slots=True)
class SearchFilters:
    topics: Sequence[str] | None = None
    sentiment: int | None = None
    stance: str | None = None
    since_days: int | None = None


def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def semantic_search(
    session: AsyncSession,
    lm_client: LMStudioClient,
    query: str,
    filters: SearchFilters | None = None,
    limit: int = 20,
) -> list[tuple[Item, float]]:
    embedding = (await lm_client.get_embeddings([query]))[0]
    stmt = select(Item)
    clauses = []
    if filters:
        if filters.sentiment is not None:
            clauses.append(Item.sentiment == filters.sentiment)
        if filters.stance:
            clauses.append(Item.stance == filters.stance)
        if filters.since_days:
            since_dt = datetime.now(tz=timezone.utc) - timedelta(days=filters.since_days)
            clauses.append(Item.published_at >= since_dt)
    if clauses:
        stmt = stmt.where(and_(*clauses))
    result = await session.execute(stmt)
    items = result.scalars().all()
    scored: list[tuple[Item, float]] = []
    for item in items:
        if not item.embedding:
            continue
        if filters and filters.topics:
            if not set(filters.topics).intersection(set(item.topics or [])):
                continue
        score = _cosine_similarity(embedding, item.embedding)
        scored.append((item, score))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]
