from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 0

URL_RE = re.compile(r"https?://\S+")
EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "]+",
    flags=re.UNICODE,
)
MULTISPACE_RE = re.compile(r"\s+")
RT_PREFIX_RE = re.compile(r"^RT @[^:]+: ")


def normalize_text(text: str) -> str:
    """Normalize text by removing URLs, emojis, RT markers, and collapsing whitespace."""

    text = unicodedata.normalize("NFC", text)
    text = URL_RE.sub("", text)
    text = EMOJI_RE.sub("", text)
    text = RT_PREFIX_RE.sub("", text)
    text = MULTISPACE_RE.sub(" ", text)
    return text.strip()


def detect_language(text: str) -> str | None:
    cleaned = text.strip()
    if not cleaned:
        return None
    try:
        lang = detect(cleaned)
    except LangDetectException:
        return None
    return lang


def truncate_tokens(text: str, max_tokens: int) -> str:
    words = text.split()
    if len(words) <= max_tokens:
        return text
    return " ".join(words[:max_tokens])


def iter_chunks(iterable: Iterable[str], size: int) -> Iterable[list[str]]:
    batch: list[str] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch
