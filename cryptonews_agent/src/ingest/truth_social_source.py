from __future__ import annotations

from datetime import datetime
from typing import Any, List

try:  # pragma: no cover - optional dependency
    from mastodon import Mastodon
except Exception:  # pragma: no cover
    Mastodon = None  # type: ignore

from src.ingest.base import BaseSource, NormalizedItem
from src.ingest.normalizer import detect_language, normalize_text, truncate_tokens


class TruthSocialSource(BaseSource):
    def __init__(self, client: Mastodon | None, max_tokens: int = 1500) -> None:
        from src.db.models import SourceEnum

        super().__init__("truth_social", SourceEnum.truth_social)
        self._client = client
        self._max_tokens = max_tokens

    async def fetch_since(self, since_dt: datetime) -> List[NormalizedItem]:
        if self._client is None:
            return []
        timeline = self._client.timeline_public(limit=100)
        items: list[NormalizedItem] = []
        for status in timeline:
            published_at = datetime.fromisoformat(status["created_at"].replace("Z", "+00:00"))
            if published_at <= since_dt:
                continue
            items.append(await self.normalize(status))
        return items

    async def normalize(self, raw: Any) -> NormalizedItem:
        text = raw.get("content", "")
        text = truncate_tokens(normalize_text(text), self._max_tokens)
        lang = raw.get("language") or detect_language(text)
        published_at = datetime.fromisoformat(raw["created_at"].replace("Z", "+00:00"))
        author = raw.get("account", {}).get("acct")
        source_id = str(raw.get("id"))
        return NormalizedItem(
            source=self.source_enum,
            source_id=source_id,
            text=text,
            raw=raw,
            published_at=published_at,
            author=author,
            lang=lang,
        )
