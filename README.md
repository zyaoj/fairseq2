# Urology Data Platform

Multi-modal patient data platform for urology that aggregates lab results, imaging, and clinical notes with AI-powered extraction and summarization.

## Quick Start

```bash
# Install pixi (if not already installed)
curl -fsSL https://pixi.sh/install.sh | bash

# Install dependencies
pixi install

# Start infrastructure (install docker-compose first: brew install docker-compose)
docker-compose up -d

# Run migrations
pixi run alembic upgrade head

# Start backend
pixi run uvicorn src.main:app --reload

# Start UI (separate terminal)
pixi run streamlit run ui/app.py
```

## Project Structure

```
urology-data-platform/
├── src/
│   ├── main.py           # FastAPI entry point
│   ├── api/              # API routers
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   └── core/             # Config, security, database
├── ui/                   # Streamlit frontend
├── tests/                # Test suite
└── docker-compose.yml    # Infrastructure
```

## Development

```bash
# Run tests
pixi run pytest

# Run linting
pixi run ruff check src tests

# Run type checking
pixi run mypy src
```
