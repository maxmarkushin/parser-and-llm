from __future__ import annotations

import json

import pytest

pytest.importorskip("pydantic")

from src.llm.schema import ClassificationResult


def test_classification_result_parse_json_valid() -> None:
    payload = {
        "topics": ["crypto"],
        "sentiment": 1,
        "stance": "bullish",
        "impact": 2,
        "tickers": ["BTC"],
        "entities": [{"type": "ORG", "text": "SEC"}],
    }
    result = ClassificationResult.parse_json(json.dumps(payload))
    assert result.sentiment == 1
    assert result.entities[0].text == "SEC"


def test_classification_result_parse_json_invalid() -> None:
    with pytest.raises(ValueError):
        ClassificationResult.parse_json("not json")
