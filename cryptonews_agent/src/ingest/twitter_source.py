from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, List, Sequence

try:  # pragma: no cover - optional dependency
    import tweepy
except Exception:  # pragma: no cover
    tweepy = None  # type: ignore

from src.ingest.base import BaseSource, NormalizedItem
from src.ingest.normalizer import detect_language, normalize_text, truncate_tokens


class TwitterSource(BaseSource):
    def __init__(
        self,
        client: tweepy.Client | None,
        queries: Sequence[str],
        max_tokens: int = 1500,
    ) -> None:
        from src.db.models import SourceEnum

        super().__init__("twitter", SourceEnum.twitter)
        self._client = client
        self._queries = list(queries)
        self._max_tokens = max_tokens

    async def fetch_since(self, since_dt: datetime) -> List[NormalizedItem]:
        if self._client is None:
            return []
        if not self._queries:
            return []

        query = " OR ".join(self._queries)
        params = {
            "query": query,
            "start_time": since_dt.isoformat().replace("+00:00", "Z"),
            "tweet_fields": ["author_id", "created_at", "lang"],
            "max_results": 100,
        }

        def _search() -> Any:
            return self._client.search_recent_tweets(**params)

        response = await asyncio.to_thread(_search)
        data = getattr(response, "data", None) or []
        items: list[NormalizedItem] = []
        for tweet in data:
            items.append(await self.normalize(tweet))
        return items

    async def normalize(self, raw: Any) -> NormalizedItem:
        text = truncate_tokens(normalize_text(raw.text), self._max_tokens)
        lang = raw.lang or detect_language(text)
        published_at = raw.created_at
        if isinstance(published_at, str):
            published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return NormalizedItem(
            source=self.source_enum,
            source_id=str(raw.id),
            text=text,
            raw=raw.data if hasattr(raw, "data") else raw,
            published_at=published_at,
            author=getattr(raw, "author_id", None),
            lang=lang,
        )
