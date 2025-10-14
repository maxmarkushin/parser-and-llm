from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Item, SourceEnum
from src.ingest.base import NormalizedItem
from src.llm.schema import ClassificationResult


async def get_item_by_source_id(session: AsyncSession, source_id: str) -> Item | None:
    stmt = select(Item).where(Item.source_id == source_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_item(
    session: AsyncSession,
    normalized: NormalizedItem,
    classification: ClassificationResult | None,
    embedding: Sequence[float] | None,
) -> Item:
    existing = await get_item_by_source_id(session, normalized.source_id)
    payload = {
        "source": SourceEnum(normalized.source),
        "source_id": normalized.source_id,
        "author": normalized.author,
        "published_at": normalized.published_at,
        "lang": normalized.lang,
        "text": normalized.text,
        "raw": normalized.raw,
        "tickers": classification.tickers if classification else [],
        "entities": [entity.model_dump() for entity in classification.entities]
        if classification
        else [],
        "topics": classification.topics if classification else [],
        "sentiment": classification.sentiment if classification else None,
        "stance": classification.stance if classification else None,
        "impact": classification.impact if classification else None,
        "embedding": list(embedding) if embedding is not None else None,
    }

    if existing:
        for key, value in payload.items():
            setattr(existing, key, value)
        return existing

    item = Item(**payload)
    session.add(item)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing = await get_item_by_source_id(session, normalized.source_id)
        if existing is None:
            raise
        return existing
    return item


async def upsert_items(
    session: AsyncSession,
    items: Iterable[tuple[NormalizedItem, ClassificationResult | None, Sequence[float] | None]],
) -> list[Item]:
    results: list[Item] = []
    for normalized, classification, embedding in items:
        results.append(await upsert_item(session, normalized, classification, embedding))
    return results
