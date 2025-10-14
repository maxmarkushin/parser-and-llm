from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import List

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import get_settings
from src.ingest.reddit_source import RedditSource
from src.ingest.telegram_source import TelegramSource
from src.ingest.truth_social_source import TruthSocialSource
from src.ingest.twitter_source import TwitterSource
from src.llm.client import LMStudioClient
from src.pipeline.worker import PipelineWorker

logger = logging.getLogger(__name__)


async def _build_sources() -> list:
    settings = get_settings()
    sources = []

    if settings.enable_telegram:
        try:
            from telethon import TelegramClient  # type: ignore

            client = None
            if settings.telegram_api_id and settings.telegram_api_hash:
                client = TelegramClient(
                    "cryptonews_agent",
                    settings.telegram_api_id,
                    settings.telegram_api_hash,
                    system_version="4.16.30-vx",
                )
                await client.connect()
            sources.append(
                TelegramSource(client, settings.telegram_channels, settings.max_text_tokens)
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to initialize Telegram client", extra={"error": str(exc)})

    if settings.enable_twitter:
        try:
            import tweepy

            client = None
            if settings.twitter_bearer_token:
                client = tweepy.Client(bearer_token=settings.twitter_bearer_token, wait_on_rate_limit=True)
            sources.append(TwitterSource(client, settings.telegram_channels, settings.max_text_tokens))
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to initialize Twitter client", extra={"error": str(exc)})

    if settings.enable_reddit:
        try:
            import praw

            client = None
            if settings.reddit_client_id and settings.reddit_client_secret:
                client = praw.Reddit(
                    client_id=settings.reddit_client_id,
                    client_secret=settings.reddit_client_secret,
                    user_agent="cryptonews-agent",
                )
            sources.append(RedditSource(client, settings.reddit_subreddits, settings.max_text_tokens))
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to initialize Reddit client", extra={"error": str(exc)})

    if settings.enable_truth_social:
        try:
            from mastodon import Mastodon

            client = None
            if settings.truth_social_access_token:
                client = Mastodon(
                    access_token=settings.truth_social_access_token,
                    api_base_url=settings.truth_social_base_url,
                )
            sources.append(TruthSocialSource(client, settings.max_text_tokens))
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to initialize Truth Social client", extra={"error": str(exc)})

    return sources


async def start_scheduler() -> None:
    settings = get_settings()
    sources = await _build_sources()
    sources = [source for source in sources if source is not None]
    if not sources:
        logger.warning("No sources configured; scheduler will idle")
    lm_client = LMStudioClient()
    worker = PipelineWorker(sources, lm_client, settings.batch_size, settings.worker_concurrency)
    await worker.start()

    scheduler = AsyncIOScheduler(timezone="UTC")

    async def enqueue_source(name: str) -> None:
        await worker.enqueue(name, datetime.now(tz=timezone.utc) - timezone.utc.utcoffset(None))

    for source in sources:
        scheduler.add_job(
            lambda src=source.name: asyncio.create_task(worker.enqueue(src)),
            "interval",
            seconds=settings.fetch_interval_seconds,
            next_run_time=datetime.now(tz=timezone.utc),
        )

    scheduler.start()

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Stopping scheduler")
    finally:
        scheduler.shutdown(wait=False)
        await worker.stop()
