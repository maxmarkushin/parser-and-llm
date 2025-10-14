from __future__ import annotations

import enum
import uuid
from typing import Any, List, Sequence

from sqlalchemy import JSON, DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator

from src.db.base import Base

try:  # pragma: no cover - optional dependency
    from pgvector.sqlalchemy import Vector as PGVector
except Exception:  # pragma: no cover
    PGVector = None


class SourceEnum(str, enum.Enum):
    telegram = "telegram"
    twitter = "twitter"
    reddit = "reddit"
    truth_social = "truth_social"


class StringArray(TypeDecorator[List[str]]):
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        if dialect.name == "postgresql":  # pragma: no branch - simple dialect switch
            from sqlalchemy.dialects.postgresql import ARRAY

            return dialect.type_descriptor(ARRAY(String))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Sequence[str] | None, dialect):  # type: ignore[override]
        if value is None:
            return value
        return list(value)

    def process_result_value(self, value, dialect):  # type: ignore[override]
        if value is None:
            return []
        return list(value)


class EmbeddingType(TypeDecorator[List[float]]):
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        if PGVector is not None and dialect.name == "postgresql":
            return dialect.type_descriptor(PGVector(dim=768))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Sequence[float] | None, dialect):  # type: ignore[override]
        if value is None:
            return None
        return list(value)

    def process_result_value(self, value, dialect):  # type: ignore[override]
        if value is None:
            return None
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                import json

                return json.loads(value)
            except Exception:  # pragma: no cover - fallback
                return None
        return value


class Item(Base):
    __tablename__ = "items"

    id: Mapped[uuid.UUID] = mapped_column(
        default=uuid.uuid4, primary_key=True
    )
    source: Mapped[SourceEnum] = mapped_column(Enum(SourceEnum), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    author: Mapped[str | None]
    published_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False)
    lang: Mapped[str | None] = mapped_column(String(5))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    raw: Mapped[Any] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    tickers: Mapped[List[str]] = mapped_column(StringArray, default=list)
    entities: Mapped[Any] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), default=dict)
    topics: Mapped[List[str]] = mapped_column(StringArray, default=list)
    sentiment: Mapped[int | None] = mapped_column(Integer)
    stance: Mapped[str | None] = mapped_column(String(16))
    impact: Mapped[int | None] = mapped_column(Integer)
    embedding: Mapped[List[float] | None] = mapped_column(EmbeddingType)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_items_source_published_at", "source", "published_at"),
        Index("ix_items_topics", "topics", postgresql_using="gin"),
    )
