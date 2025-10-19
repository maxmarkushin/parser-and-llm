from __future__ import annotations

from src.llm.client import LMStudioClient
from src.llm.schema import ClassificationResult

SYSTEM_PROMPT = """
You are an analyst who labels crypto and macro news. Respond ONLY with JSON that strictly
matches the provided schema. Do not add commentary.
""".strip()

USER_TEMPLATE = """
Analyze the following post and classify it according to the schema:

Text:
"""
{text}
"""

Return JSON with keys: topics (list of "crypto", "macro", "regulation", "markets" as applicable),
sentiment (-1, 0, 1), stance ("bullish", "bearish", "neutral"), impact (0-2), tickers (list of symbols),
and entities (list of objects with type/text).
""".strip()


async def classify_text(client: LMStudioClient, text: str) -> ClassificationResult:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(text=text)},
    ]
    response = await client.achat(messages, max_tokens=300)
    try:
        return ClassificationResult.parse_json(response)
    except ValueError:
        repair_messages = messages + [
            {
                "role": "user",
                "content": "Your previous response did not match the schema. Return valid JSON only.",
            }
        ]
        response = await client.achat(repair_messages, max_tokens=300)
        return ClassificationResult.parse_json(response)
