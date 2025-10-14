from __future__ import annotations

from datetime import datetime, timezone

import pytest

pytest.importorskip("langdetect")

from src.ingest.dedup import filter_duplicates
from src.ingest.normalizer import detect_language, normalize_text, truncate_tokens
from src.ingest.base import NormalizedItem
from src.db.models import SourceEnum


def test_normalize_text_removes_urls_and_emojis() -> None:
    text = "Check this https://example.com 😀"
    normalized = normalize_text(text)
    assert "http" not in normalized
    assert "😀" not in normalized


def test_detect_language_handles_empty() -> None:
    assert detect_language("") is None


def test_filter_duplicates() -> None:
    items = [
        NormalizedItem(
            source=SourceEnum.reddit,
            source_id="1",
            text="Hello world",
            raw={},
            published_at=datetime.now(tz=timezone.utc),
        ),
        NormalizedItem(
            source=SourceEnum.reddit,
            source_id="2",
            text="Hello world",
            raw={},
            published_at=datetime.now(tz=timezone.utc),
        ),
    ]
    deduped = filter_duplicates(items)
    assert len(deduped) == 1


def test_truncate_tokens_limits_length() -> None:
    text = " ".join(["token"] * 10)
    truncated = truncate_tokens(text, max_tokens=5)
    assert len(truncated.split()) == 5
