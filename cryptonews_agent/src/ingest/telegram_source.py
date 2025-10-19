from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Sequence

try:  # pragma: no cover - optional dependency
    from telethon import TelegramClient
    from telethon.errors import TelethonError
except Exception:  # pragma: no cover
    TelegramClient = None  # type: ignore
    TelethonError = Exception  # type: ignore

from src.ingest.base import BaseSource, NormalizedItem
from src.ingest.normalizer import detect_language, normalize_text, truncate_tokens


class TelegramSource(BaseSource):
    def __init__(
        self,
        client: TelegramClient | None,
        channels: Sequence[str],
        max_tokens: int = 1500,
    ) -> None:
        from src.db.models import SourceEnum

        super().__init__("telegram", SourceEnum.telegram)
        self._client = client
        self._channels = list(channels)
        self._max_tokens = max_tokens

    async def fetch_since(self, since_dt: datetime) -> List[NormalizedItem]:
        if self._client is None:
            return []
        items: list[NormalizedItem] = []
        for channel in self._channels:
            try:
                async for message in self._client.iter_messages(channel, offset_date=since_dt):
                    if message.date is None:
                        continue
                    if message.date.replace(tzinfo=timezone.utc) <= since_dt.replace(
                        tzinfo=timezone.utc
                    ):
                        break
                    normalized = await self.normalize({"channel": channel, "message": message})
                    items.append(normalized)
            except TelethonError:
                continue
        return items

    async def normalize(self, raw: Any) -> NormalizedItem:
        message = raw["message"]
        channel = raw["channel"]
        text = message.message or ""
        text = truncate_tokens(normalize_text(text), self._max_tokens)
        lang = detect_language(text)
        raw_payload = {
            "channel": channel,
            "message": message.to_dict() if hasattr(message, "to_dict") else str(message),
        }
        published_at = message.date
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        return NormalizedItem(
            source=self.source_enum,
            source_id=f"{channel}:{message.id}",
            text=text,
            raw=raw_payload,
            published_at=published_at,
            author=getattr(message, "sender_id", None),
            lang=lang,
        )
