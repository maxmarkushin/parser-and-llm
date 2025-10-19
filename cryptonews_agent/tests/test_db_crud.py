from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

import pytest

pytest.importorskip("sqlalchemy")

from src.config import get_settings
from src.db import base, crud
from src.db.base import Base, get_engine, get_session
from src.db.models import SourceEnum
from src.ingest.base import NormalizedItem
from src.llm.schema import ClassificationResult, Entity


@pytest.mark.asyncio
async def test_upsert_item_sqlite(monkeypatch) -> None:
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", ":memory:")
    get_settings.cache_clear()  # type: ignore[attr-defined]
    base._engine = None  # type: ignore[attr-defined]
    base._session_factory = None  # type: ignore[attr-defined]

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    normalized = NormalizedItem(
        source=SourceEnum.reddit,
        source_id="abc",
        text="Bitcoin is rising",
        raw={"id": "abc"},
        published_at=datetime.now(tz=timezone.utc),
        lang="en",
    )
    classification = ClassificationResult(
        topics=["crypto"],
        sentiment=1,
        stance="bullish",
        impact=2,
        tickers=["BTC"],
        entities=[Entity(type="ORG", text="SEC")],
    )

    async with get_session() as session:
        item = await crud.upsert_item(session, normalized, classification, [0.1, 0.2])
        assert item.source_id == "abc"
        assert item.topics == ["crypto"]
        assert item.embedding == [0.1, 0.2]

    # Upsert again with different sentiment to ensure update
    classification.sentiment = -1
    async with get_session() as session:
        item = await crud.upsert_item(session, normalized, classification, [0.1, 0.2])
        assert item.sentiment == -1
