from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field, ValidationError


class Entity(BaseModel):
    type: str = Field(..., description="Entity type such as ORG/PER/TOPIC")
    text: str = Field(..., description="Mention text")


class ClassificationResult(BaseModel):
    topics: List[str] = Field(default_factory=list)
    sentiment: Literal[-1, 0, 1]
    stance: Literal["bullish", "bearish", "neutral"]
    impact: Literal[0, 1, 2]
    tickers: List[str] = Field(default_factory=list)
    entities: List[Entity] = Field(default_factory=list)

    @classmethod
    def parse_json(cls, json_str: str) -> "ClassificationResult":
        import json

        try:
            payload = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise ValueError("Failed to decode JSON") from exc
        try:
            return cls.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
