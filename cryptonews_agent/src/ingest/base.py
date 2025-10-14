from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Protocol

from src.db.models import SourceEnum


@dataclass(slots=True)
class NormalizedItem:
    source: SourceEnum
    source_id: str
    text: str
    raw: Any
    published_at: datetime
    author: str | None = None
    lang: str | None = None
    content_hash: str | None = None


class Source(Protocol):
    name: str

    async def fetch_since(self, since_dt: datetime) -> List[NormalizedItem]:
        ...

    async def normalize(self, raw: Any) -> NormalizedItem:
        ...


class BaseSource(abc.ABC):
    def __init__(self, name: str, source_enum: SourceEnum) -> None:
        self.name = name
        self.source_enum = source_enum

    @abc.abstractmethod
    async def fetch_since(self, since_dt: datetime) -> List[NormalizedItem]:
        raise NotImplementedError

    @abc.abstractmethod
    async def normalize(self, raw: Any) -> NormalizedItem:
        raise NotImplementedError
