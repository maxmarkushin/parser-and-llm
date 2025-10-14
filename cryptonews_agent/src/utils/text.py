from __future__ import annotations

import re

WHITESPACE_RE = re.compile(r"\s+")


def collapse_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def ensure_max_length(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"
