from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy import select

from src.config import get_settings
from src.db import base
from src.db.base import Base, get_engine, get_session
from src.db.models import Item, SourceEnum
from src.ingest.base import BaseSource, NormalizedItem
from src.pipeline.worker import PipelineWorker


class DummySource(BaseSource):
    def __init__(self) -> None:
        super().__init__("reddit", SourceEnum.reddit)
        self._emitted = False

    async def fetch_since(self, since: datetime) -> list[NormalizedItem]:
        if self._emitted:
            return []
        self._emitted = True
        return [
            NormalizedItem(
                source=self.source_enum,
                source_id="dummy",
                text="Bitcoin pumps hard",
                raw={},
                published_at=datetime.now(tz=timezone.utc),
                lang="en",
            )
        ]

    async def normalize(self, raw):
        raise NotImplementedError


class DummyLMClient:
    async def warmup(self) -> None:
        return None

    async def achat(self, messages, max_tokens: int | None = None) -> str:
        return json.dumps(
            {
                "topics": ["crypto"],
                "sentiment": 1,
                "stance": "bullish",
                "impact": 2,
                "tickers": ["BTC"],
                "entities": [{"type": "ORG", "text": "SEC"}],
            }
        )

    async def get_embeddings(self, texts):
        return [[0.1, 0.2] for _ in texts]


@pytest.mark.asyncio
async def test_pipeline_worker_persists_items(monkeypatch) -> None:
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", ":memory:")
    get_settings.cache_clear()  # type: ignore[attr-defined]
    base._engine = None  # type: ignore[attr-defined]
    base._session_factory = None  # type: ignore[attr-defined]

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    source = DummySource()
    worker = PipelineWorker([source], DummyLMClient(), batch_size=10, concurrency=1)
    await worker.start()
    await worker.enqueue(source.name, datetime.now(tz=timezone.utc) - timedelta(minutes=5))
    await asyncio.wait_for(worker.join(), timeout=5)
    await worker.stop()

    async with get_session() as session:
        result = await session.execute(select(Item))
        items = result.scalars().all()
        assert len(items) == 1
        assert items[0].topics == ["crypto"]
        assert items[0].embedding is not None
