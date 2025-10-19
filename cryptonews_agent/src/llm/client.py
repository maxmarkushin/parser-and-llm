from __future__ import annotations

import logging
from typing import Sequence

from openai import AsyncOpenAI
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config import get_settings

logger = logging.getLogger(__name__)


class LMStudioClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(
            api_key=settings.lmstudio_api_key,
            base_url=str(settings.lmstudio_base_url),
        )
        self._model = settings.llm_model
        self._embed_model = settings.embed_model
        self._temperature = 0.2
        self._top_p = 0.9
        self._max_tokens = 1024
        self._warmed = False

    async def warmup(self) -> None:
        if self._warmed:
            return
        try:
            await self.achat([
                {"role": "system", "content": "You are warming up."},
                {"role": "user", "content": "OK"},
            ], max_tokens=1)
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("Warmup failed", extra={"error": str(exc)})
        self._warmed = True

    async def achat(self, messages: Sequence[dict[str, str]], max_tokens: int | None = None) -> str:
        max_tokens = max_tokens or self._max_tokens

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        ):
            with attempt:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    temperature=self._temperature,
                    top_p=self._top_p,
                    max_tokens=max_tokens,
                    messages=list(messages),
                )
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError("Empty response from LM Studio")
                return content
        raise RuntimeError("Failed to obtain chat completion")

    async def get_embeddings(self, texts: Sequence[str]) -> list[list[float]]:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        ):
            with attempt:
                response = await self._client.embeddings.create(model=self._embed_model, input=list(texts))
                return [data.embedding for data in response.data]
        raise RuntimeError("Failed to compute embeddings")
