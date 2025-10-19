from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, List, Sequence

try:  # pragma: no cover - optional dependency
    import praw
except Exception:  # pragma: no cover
    praw = None  # type: ignore

from src.ingest.base import BaseSource, NormalizedItem
from src.ingest.normalizer import detect_language, normalize_text, truncate_tokens


class RedditSource(BaseSource):
    def __init__(
        self,
        client: praw.Reddit | None,
        subreddits: Sequence[str],
        max_tokens: int = 1500,
    ) -> None:
        from src.db.models import SourceEnum

        super().__init__("reddit", SourceEnum.reddit)
        self._client = client
        self._subreddits = list(subreddits)
        self._max_tokens = max_tokens

    async def fetch_since(self, since_dt: datetime) -> List[NormalizedItem]:
        if self._client is None:
            return []
        items: list[NormalizedItem] = []
        for subreddit_name in self._subreddits:
            subreddit = self._client.subreddit(subreddit_name)
            for submission in subreddit.new(limit=100):
                created = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                if created <= since_dt.replace(tzinfo=timezone.utc):
                    continue
                items.append(await self.normalize(submission))
        return items

    async def normalize(self, raw: Any) -> NormalizedItem:
        text = raw.selftext or raw.title or ""
        text = truncate_tokens(normalize_text(text), self._max_tokens)
        lang = detect_language(text)
        published_at = datetime.fromtimestamp(raw.created_utc, tz=timezone.utc)
        payload = {
            "id": raw.id,
            "subreddit": raw.subreddit.display_name if hasattr(raw, "subreddit") else None,
            "title": raw.title,
            "url": raw.url,
        }
        return NormalizedItem(
            source=self.source_enum,
            source_id=raw.name if hasattr(raw, "name") else str(raw.id),
            text=text,
            raw=payload,
            published_at=published_at,
            author=getattr(raw, "author", None).name if getattr(raw, "author", None) else None,
            lang=lang,
        )
