from __future__ import annotations

import asyncio
from datetime import datetime
from typing import List, Optional

import typer
from rich import print

from src.config import get_settings
from src.db.base import Base, get_engine, get_session
from src.logging_conf import configure_logging
from src.pipeline.scheduler import start_scheduler
from src.pipeline.worker import PipelineWorker
from src.search.query import SearchFilters, semantic_search
from src.utils.time import parse_iso8601, utc_now

app = typer.Typer(help="CryptoNews Agent CLI")
ingest_app = typer.Typer(help="Ingestion commands")
db_app = typer.Typer(help="Database migration commands")
app.add_typer(ingest_app, name="ingest")
app.add_typer(db_app, name="db")


async def _build_worker() -> PipelineWorker:
    from src.pipeline.scheduler import _build_sources
    from src.llm.client import LMStudioClient

    settings = get_settings()
    sources = await _build_sources()
    sources = [source for source in sources if source is not None]
    client = LMStudioClient()
    worker = PipelineWorker(sources, client, settings.batch_size, settings.worker_concurrency)
    await worker.start()
    return worker


@ingest_app.command("run")
def ingest_run(since: Optional[str] = typer.Option(None, help="ISO8601 start time")) -> None:
    """Run a one-off ingestion job."""

    configure_logging()

    async def _run() -> None:
        worker = await _build_worker()
        target_since = parse_iso8601(since) if since else utc_now()
        for source_name in worker.source_names:
            await worker.enqueue(source_name, target_since)
        await asyncio.wait_for(worker.join(), timeout=None)
        await worker.stop()

    asyncio.run(_run())


@app.command("scheduler")
def scheduler_start() -> None:
    """Start the APScheduler-based pipeline."""

    configure_logging()
    asyncio.run(start_scheduler())


@app.command()
def search(
    query: str = typer.Argument(..., help="Query text"),
    topics: Optional[str] = typer.Option(None, help="Comma-separated topics"),
    days: Optional[int] = typer.Option(None, help="Restrict to last N days"),
    stance: Optional[str] = typer.Option(None, help="Filter by stance"),
    sentiment: Optional[int] = typer.Option(None, help="Filter by sentiment"),
) -> None:
    """Run a semantic search query."""

    configure_logging()

    async def _search() -> None:
        from src.llm.client import LMStudioClient

        lm_client = LMStudioClient()
        filters = SearchFilters(
            topics=topics.split(",") if topics else None,
            sentiment=sentiment,
            stance=stance,
            since_days=days,
        )
        async with get_session() as session:
            results = await semantic_search(session, lm_client, query, filters=filters)
        for item, score in results:
            print(f"[bold]{item.source.value}:{item.source_id}[/bold] score={score:.3f}")
            print(f"Topics: {item.topics} Sentiment: {item.sentiment} Stance: {item.stance}")
            print(item.text)
            print("-")

    asyncio.run(_search())


@db_app.command("init")
def db_init() -> None:
    """Create database tables without migrations."""

    configure_logging()

    async def _init() -> None:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())


@db_app.command("migrate")
def db_migrate(message: str = typer.Argument(..., help="Migration message")) -> None:
    """Create a new Alembic revision."""

    from alembic import command
    from alembic.config import Config

    configure_logging()
    settings = get_settings()
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.get_database_url())
    command.revision(alembic_cfg, message=message, autogenerate=True)


@db_app.command("upgrade")
def db_upgrade(revision: str = "head") -> None:
    """Run Alembic upgrade."""

    from alembic import command
    from alembic.config import Config

    configure_logging()
    settings = get_settings()
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.get_database_url())
    command.upgrade(alembic_cfg, revision)


if __name__ == "__main__":
    app()
