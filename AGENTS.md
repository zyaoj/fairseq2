# Repository Guidelines

## Project Structure & Module Organization
- **Backend:** `src/main.py` starts the FastAPI app; routers live in `src/api/`; shared config/security/DB helpers in `src/core/`; domain logic in `src/services/`; data models in `src/models/` and `src/schemas/`; background tasks/workers in `src/workers/`; internationalization strings in `src/i18n/`; document templates in `src/word_templates/`.
- **Data & migrations:** Alembic scripts are in `alembic/versions/`; reference schemas and vocab live under `reference/` and `src/entity_schemas/`.
- **Frontend:** Streamlit UI in `ui/` (entrypoint `ui/app.py`).
- **Docs & scripts:** Developer docs in `docs/`; utility scripts in `scripts/`.
- **Tests:** Pytest suite in `tests/` (uses in-memory SQLite via `tests/conftest.py`).

## Build, Test, and Development Commands
- Install toolchain & deps: `pixi install`
- Start infra: `docker-compose up -d`
- Run DB migrations: `pixi run alembic upgrade head`
- Run API locally: `pixi run uvicorn src.main:app --reload`
- Run UI: `pixi run streamlit run ui/app.py`
- Lint: `pixi run ruff check src tests` (add `--fix` to autoformat)
- Type check: `pixi run mypy src`
- Tests: `pixi run pytest` or `pixi run pytest tests/test_auth.py` for a single module

## Coding Style & Naming Conventions
- Python 3.11, type hints required; mypy is strict.
- Ruff line length is 100; follow PEP8 with snake_case for functions/vars, PascalCase for classes, and RESTful, lowercase-with-dashes endpoints.
- Keep API schemas in Pydantic models under `src/schemas/`; persist entities in SQLAlchemy models under `src/models/`.
- Co-locate router-specific services/tests with their domain folder when practical.

## Testing Guidelines
- Use pytest with the provided in-memory SQLite fixtures; avoid relying on external services in unit tests.
- Name tests `test_*` and keep fast, isolated cases; prefer API-level tests via `TestClient` for routers.
- Before PRs, run `pixi run pytest`, `pixi run ruff check src tests`, and `pixi run mypy src`.

## Commit & Pull Request Guidelines
- Follow the repo’s history style: short, imperative messages with prefixes like `feat:`, `fix:`, `docs:` (e.g., `feat: add followup scheduling API`).
- Include in PRs: summary of changes, breaking/migration notes (especially Alembic), tests executed, and screenshots/GIFs for UI changes.
- Link related issues/tasks and call out configuration/env changes (.env, Docker, S3/MinIO, Milvus, database URL).

## Security & Configuration Tips
- Populate secrets via `.env` (see `src/core/config.py`); the default secret key is dev-only—replace for any deployment.
- Keep credentials for Postgres, MinIO, Milvus, and external AI APIs out of commits; use environment variables.
- If you use the multi-agent workflow, see `docs/Multi-Agent Build-Review Framework.md` for builder/reviewer handoffs.
