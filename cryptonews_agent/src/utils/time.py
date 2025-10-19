from __future__ import annotations

from datetime import datetime, timezone
from dateutil import parser


def parse_iso8601(value: str) -> datetime:
    dt = parser.isoparse(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)
