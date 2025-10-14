from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Sequence

from src.config import get_settings
from src.db import crud
from src.db.base import get_session
from src.ingest.base import NormalizedItem, Source
from src.ingest.dedup import filter_duplicates, mark_hash
from src.llm.classifiers import classify_text
from src.llm.client import LMStudioClient
from src.llm.schema import ClassificationResult

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Job:
    source_name: str
    since: datetime


class PipelineWorker:
    def __init__(
        self,
        sources: Sequence[Source],
        lm_client: LMStudioClient,
        batch_size: int,
        concurrency: int,
    ) -> None:
        self._sources = {source.name: source for source in sources}
        self._lm_client = lm_client
        self._batch_size = batch_size
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._tasks: list[asyncio.Task[None]] = []
        self._concurrency = concurrency
        self._embedding_cache: Dict[str, List[float]] = {}
        self._last_seen: Dict[str, datetime] = {}
        self._stopping = False

    async def start(self) -> None:
        await self._lm_client.warmup()
        for _ in range(self._concurrency):
            task = asyncio.create_task(self._worker())
            self._tasks.append(task)

    async def stop(self) -> None:
        self._stopping = True
        for _ in self._tasks:
            await self._queue.put(Job(source_name="__stop__", since=datetime.utcnow()))
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def enqueue(self, source_name: str, since: datetime | None = None) -> None:
        if source_name not in self._sources:
            logger.warning("Unknown source", extra={"source": source_name})
            return
        last_since = self._last_seen.get(source_name)
        if since is None:
            default_since = datetime.now(tz=timezone.utc) - timedelta(
                seconds=get_settings().fetch_interval_seconds * 2
            )
            since = last_since or default_since
        self._last_seen[source_name] = since
        await self._queue.put(Job(source_name=source_name, since=since))

    async def join(self) -> None:
        await self._queue.join()

    @property
    def source_names(self) -> list[str]:
        return list(self._sources.keys())

    async def _worker(self) -> None:
        while True:
            job = await self._queue.get()
            if job.source_name == "__stop__":
                self._queue.task_done()
                break
            try:
                await self._process_job(job)
            except Exception as exc:
                logger.exception("Job processing failed", extra={"source": job.source_name, "error": str(exc)})
            finally:
                self._queue.task_done()

    async def _process_job(self, job: Job) -> None:
        source = self._sources[job.source_name]
        since = job.since.astimezone(timezone.utc)
        logger.info("Fetching", extra={"source": source.name, "since": since.isoformat()})
        items = await source.fetch_since(since)
        if not items:
            return
        mark_hash(items)
        items = filter_duplicates(items)
        logger.info("Processing items", extra={"source": source.name, "count": len(items)})
        await self._enrich_and_store(items)
        latest = max(item.published_at for item in items)
        if latest:
            self._last_seen[source.name] = latest

    async def _enrich_and_store(self, items: Sequence[NormalizedItem]) -> None:
        enriched: list[tuple[NormalizedItem, ClassificationResult | None, List[float] | None]] = []
        for item in items:
            classification = None
            try:
                if item.text:
                    classification = await classify_text(self._lm_client, item.text)
            except Exception as exc:
                logger.warning("Classification failed", extra={"error": str(exc)})
            embedding = None
            if item.content_hash and item.content_hash in self._embedding_cache:
                embedding = self._embedding_cache[item.content_hash]
            elif item.text:
                embedding = await self._embed_texts([item.text])
                if embedding:
                    embedding = embedding[0]
                    if item.content_hash:
                        self._embedding_cache[item.content_hash] = embedding
            enriched.append((item, classification, embedding))
        async with get_session() as session:
            await crud.upsert_items(session, enriched)

    async def _embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []
        return await self._lm_client.get_embeddings(texts)
