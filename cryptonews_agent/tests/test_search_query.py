from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("sqlalchemy")

from src.config import get_settings
from src.db import base
from src.db.base import Base, get_engine, get_session
from src.db.models import Item, SourceEnum
from src.search.query import SearchFilters, semantic_search


class StaticLMClient:
    async def warmup(self) -> None:
        return None

    async def get_embeddings(self, texts):
        return [[1.0, 0.0] for _ in texts]


@pytest.mark.asyncio
async def test_semantic_search_filters(monkeypatch) -> None:
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", ":memory:")
    get_settings.cache_clear()  # type: ignore[attr-defined]
    base._engine = None  # type: ignore[attr-defined]
    base._session_factory = None  # type: ignore[attr-defined]

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with get_session() as session:
        session.add(
            Item(
                source=SourceEnum.reddit,
                source_id="1",
                author="alice",
                published_at=datetime.now(tz=timezone.utc) - timedelta(hours=1),
                lang="en",
                text="Bitcoin rallies",
                raw={},
                tickers=["BTC"],
                entities=[],
                topics=["crypto"],
                sentiment=1,
                stance="bullish",
                impact=2,
                embedding=[1.0, 0.0],
            )
        )
        session.add(
            Item(
                source=SourceEnum.reddit,
                source_id="2",
                author="bob",
                published_at=datetime.now(tz=timezone.utc) - timedelta(days=5),
                lang="en",
                text="Macro headwinds",
                raw={},
                tickers=[],
                entities=[],
                topics=["macro"],
                sentiment=-1,
                stance="bearish",
                impact=1,
                embedding=[0.0, 1.0],
            )
        )

    async with get_session() as session:
        results = await semantic_search(
            session,
            StaticLMClient(),
            "bitcoin",
            filters=SearchFilters(topics=["crypto"], stance="bullish", since_days=2),
        )
    assert len(results) == 1
    item, score = results[0]
    assert item.source_id == "1"
    assert score == pytest.approx(1.0)
