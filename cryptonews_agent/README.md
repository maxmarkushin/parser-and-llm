# CryptoNews Agent

CryptoNews Agent is an offline-first ingestion and analysis pipeline for crypto-related news sourced from official APIs and public feeds. It fetches posts from Telegram, X/Twitter, Reddit, and Truth Social, normalizes the content, classifies it with a local LM Studio model, and persists the enriched items with vector embeddings for semantic search.

## Features

- Pluggable ingestion adapters for Telegram, Twitter, Reddit, and Truth Social (disabled unless credentials are provided).
- Content normalization, language detection (English/Russian), and deduplication via SHA-256 hashes.
- Classification with a local LM Studio endpoint (OpenAI-compatible) including topics, sentiment, stance, impact, tickers, and entities.
- Embedding generation via LM Studio embeddings or optional SentenceTransformers fallback.
- PostgreSQL + pgvector storage with SQLite/sqlite-vec fallback.
- APScheduler-driven pipeline with asyncio workers, retries, batching, and backoff.
- Semantic search with topic/sentiment filters and cosine similarity ranking.
- CLI powered by Typer for ingestion, scheduling, database management, and search.

## Getting Started

### Prerequisites

- Python 3.11
- PostgreSQL with the `pgvector` extension (recommended) or SQLite with `sqlite-vec`.
- LM Studio running locally with an OpenAI-compatible API exposed at `http://127.0.0.1:1234/v1`.

### Installation

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\\Scripts\\activate`
pip install -U pip
pip install -e .
```

### Environment Configuration

Copy the example environment file and fill in the required settings:

```bash
cp .env.example .env
```

The most important settings are:

- `DB_BACKEND`: `postgres` or `sqlite`.
- `DATABASE_URL`: SQLAlchemy URL for PostgreSQL (e.g. `postgresql+psycopg://user:pass@localhost:5432/cryptonews`).
- `SQLITE_PATH`: Path to the SQLite database file when using the fallback backend.
- `LMSTUDIO_BASE_URL`, `LMSTUDIO_API_KEY`, `LLM_MODEL`, `EMBED_MODEL`.
- `ENABLE_*` flags and credentials for each data source.

### Database Setup

Initialize the database and run migrations:

```bash
cryptonews-agent db init
cryptonews-agent db migrate "Initial schema"
cryptonews-agent db upgrade
```

For PostgreSQL, ensure the `pgvector` extension is installed:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Running the Pipeline

Single ingest run:

```bash
cryptonews-agent ingest run --since "2025-10-13T00:00:00Z"
```

Start the scheduler (polling sources every two minutes by default):

```bash
cryptonews-agent scheduler start
```

### Search Examples

Semantic search:

```bash
cryptonews-agent search "bitcoin spot etf" --topics crypto,markets --days 7 --stance bullish
```

Bearish BTC news in last 24 hours:

```bash
cryptonews-agent search "btc" --topics crypto --days 1 --stance bearish
```

### Testing

Run the automated test suite:

```bash
pytest
```

Run type checks and linting:

```bash
ruff check
mypy src
```

## Development Notes

- The project avoids unauthorized scraping and only interacts with official APIs or public feeds.
- The LM Studio client uses the OpenAI-compatible API with configurable models and generation parameters.
- Embeddings are cached per content hash to avoid duplicate computation.
- Source adapters are optional; disable them via `.env` flags if credentials are missing.

## License

MIT
