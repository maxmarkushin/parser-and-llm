from __future__ import annotations

from functools import lru_cache
from typing import List, Literal, Optional, Sequence

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, env_prefix="")

    db_backend: Literal["postgres", "sqlite"] = Field(
        default="postgres", validation_alias="DB_BACKEND"
    )
    database_url: Optional[str] = Field(default=None, validation_alias="DATABASE_URL")
    sqlite_path: str = Field(default="./data/db.sqlite", validation_alias="SQLITE_PATH")

    lmstudio_base_url: HttpUrl = Field(
        default="http://127.0.0.1:1234/v1", validation_alias="LMSTUDIO_BASE_URL"
    )
    lmstudio_api_key: str = Field(default="lm-studio", validation_alias="LMSTUDIO_API_KEY")
    llm_model: str = Field(default="openai/gpt-oss-20b", validation_alias="LLM_MODEL")
    embed_model: str = Field(default="nomic-embed-text", validation_alias="EMBED_MODEL")

    enable_telegram: bool = Field(default=True, validation_alias="ENABLE_TELEGRAM")
    telegram_api_id: Optional[int] = Field(default=None, validation_alias="TELEGRAM_API_ID")
    telegram_api_hash: Optional[str] = Field(default=None, validation_alias="TELEGRAM_API_HASH")
    telegram_channels: List[str] = Field(
        default_factory=list, validation_alias="TELEGRAM_CHANNELS"
    )

    enable_twitter: bool = Field(default=False, validation_alias="ENABLE_TWITTER")
    twitter_bearer_token: Optional[str] = Field(
        default=None, validation_alias="TWITTER_BEARER_TOKEN"
    )

    enable_reddit: bool = Field(default=True, validation_alias="ENABLE_REDDIT")
    reddit_client_id: Optional[str] = Field(default=None, validation_alias="REDDIT_CLIENT_ID")
    reddit_client_secret: Optional[str] = Field(
        default=None, validation_alias="REDDIT_CLIENT_SECRET"
    )
    reddit_subreddits: List[str] = Field(
        default_factory=list, validation_alias="REDDIT_SUBREDDITS"
    )

    enable_truth_social: bool = Field(default=False, validation_alias="ENABLE_TRUTH_SOCIAL")
    truth_social_base_url: Optional[str] = Field(
        default="https://truthsocial.com", validation_alias="TRUTH_SOCIAL_BASE_URL"
    )
    truth_social_access_token: Optional[str] = Field(
        default=None, validation_alias="TRUTH_SOCIAL_ACCESS_TOKEN"
    )

    worker_concurrency: int = Field(default=4, validation_alias="WORKER_CONCURRENCY")
    fetch_interval_seconds: int = Field(default=120, validation_alias="FETCH_INTERVAL_SECONDS")
    batch_size: int = Field(default=50, validation_alias="BATCH_SIZE")
    max_text_tokens: int = Field(default=1500, validation_alias="MAX_TEXT_TOKENS")

    class SourcesConfig(BaseSettings):
        model_config = SettingsConfigDict(extra="ignore")

        telegram_channels: Sequence[str] = ()
        reddit_subreddits: Sequence[str] = ()

    def get_database_url(self) -> str:
        if self.db_backend == "postgres":
            if not self.database_url:
                msg = "DATABASE_URL must be provided when DB_BACKEND=postgres"
                raise ValueError(msg)
            return self.database_url
        return f"sqlite+aiosqlite:///{self.sqlite_path}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
