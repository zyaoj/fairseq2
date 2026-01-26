# Urology Data Platform Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a unified patient data platform for urologists that aggregates multi-modal medical data (starting with lab results) and uses AI for extraction and summarization.

**Architecture:** Monolith FastAPI backend with Streamlit frontend. PostgreSQL for metadata, Milvus for vector embeddings, MinIO for file storage. Claude API for VLM extraction and LLM summarization. Hybrid deployment (on-premise data, cloud AI).

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, Streamlit, PostgreSQL, Milvus, MinIO, Anthropic Claude API, pdfplumber, python-jose (JWT)

---

## Phase 1: Project Foundation

### Task 1: Initialize Python Project

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `.gitignore`
- Create: `.python-version`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "urology-data-platform"
version = "0.1.0"
description = "Multi-modal patient data platform for urology"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "sqlalchemy>=2.0.25",
    "alembic>=1.13.1",
    "psycopg2-binary>=2.9.9",
    "pydantic>=2.5.3",
    "pydantic-settings>=2.1.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.6",
    "anthropic>=0.18.0",
    "pdfplumber>=0.10.3",
    "pymilvus>=2.3.6",
    "minio>=7.2.3",
    "httpx>=0.26.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.4",
    "pytest-asyncio>=0.23.3",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.14",
    "mypy>=1.8.0",
]
ui = [
    "streamlit>=1.30.0",
    "plotly>=5.18.0",
    "pandas>=2.1.4",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 2: Create .python-version**

```
3.11
```

**Step 3: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/

# Environment
.env
.env.local

# Data
data/
uploads/
*.db

# Logs
*.log
logs/
```

**Step 4: Create README.md**

```markdown
# Urology Data Platform

A unified patient data platform for urologists that aggregates multi-modal medical data with AI-powered extraction and summarization.

## Quick Start

```bash
# Install dependencies
uv sync

# Start infrastructure
docker compose up -d

# Run migrations
uv run alembic upgrade head

# Start API server
uv run uvicorn src.main:app --reload

# Start UI (separate terminal)
uv run streamlit run ui/app.py
```

## Development

```bash
# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Run type checking
uv run mypy src/
```
```

**Step 5: Initialize git and commit**

```bash
git init
git add .
git commit -m "chore: initialize project with pyproject.toml"
```

---

### Task 2: Set Up Docker Compose Infrastructure

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`

**Step 1: Create docker-compose.yml**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: urology-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-urology}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-urology_dev}
      POSTGRES_DB: ${POSTGRES_DB:-urology_db}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-urology}"]
      interval: 5s
      timeout: 5s
      retries: 5

  milvus:
    image: milvusdb/milvus:v2.3.6
    container_name: urology-milvus
    environment:
      ETCD_USE_EMBED: "true"
      ETCD_DATA_DIR: /var/lib/milvus/etcd
      COMMON_STORAGETYPE: local
    ports:
      - "19530:19530"
      - "9091:9091"
    volumes:
      - milvus_data:/var/lib/milvus
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
      interval: 30s
      timeout: 10s
      retries: 5

  minio:
    image: minio/minio:latest
    container_name: urology-minio
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-minioadmin}
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 5

volumes:
  postgres_data:
  milvus_data:
  minio_data:
```

**Step 2: Create .env.example**

```bash
# Database
POSTGRES_USER=urology
POSTGRES_PASSWORD=urology_dev
POSTGRES_DB=urology_db
DATABASE_URL=postgresql://urology:urology_dev@localhost:5432/urology_db

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_ENDPOINT=localhost:9000
MINIO_BUCKET=urology-files

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# API
SECRET_KEY=your-secret-key-change-in-production
API_HOST=0.0.0.0
API_PORT=8000

# Anthropic
ANTHROPIC_API_KEY=your-api-key
```

**Step 3: Copy to .env and start infrastructure**

```bash
cp .env.example .env
docker compose up -d
```

Expected: All three containers start and become healthy.

**Step 4: Commit**

```bash
git add .
git commit -m "chore: add docker-compose for postgres, milvus, minio"
```

---

### Task 3: Create Core Configuration Module

**Files:**
- Create: `src/__init__.py`
- Create: `src/core/__init__.py`
- Create: `src/core/config.py`
- Test: `tests/__init__.py`
- Test: `tests/test_core/__init__.py`
- Test: `tests/test_core/test_config.py`

**Step 1: Create directory structure**

```bash
mkdir -p src/core tests/test_core
touch src/__init__.py src/core/__init__.py tests/__init__.py tests/test_core/__init__.py
```

**Step 2: Write the failing test**

Create `tests/test_core/test_config.py`:

```python
import os
from unittest.mock import patch


def test_settings_loads_from_env():
    """Settings should load values from environment variables."""
    env_vars = {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "SECRET_KEY": "test-secret-key",
        "ANTHROPIC_API_KEY": "test-api-key",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        from src.core.config import Settings
        settings = Settings()
        assert settings.database_url == "postgresql://test:test@localhost/test"
        assert settings.secret_key == "test-secret-key"
        assert settings.anthropic_api_key == "test-api-key"


def test_settings_has_defaults():
    """Settings should have sensible defaults."""
    from src.core.config import Settings
    settings = Settings()
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
    assert settings.milvus_host == "localhost"
    assert settings.milvus_port == 19530
```

**Step 3: Run test to verify it fails**

```bash
uv run pytest tests/test_core/test_config.py -v
```

Expected: FAIL with "ModuleNotFoundError" or "cannot import name 'Settings'"

**Step 4: Write minimal implementation**

Create `src/core/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql://urology:urology_dev@localhost:5432/urology_db"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "urology-files"
    minio_secure: bool = False

    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection: str = "lab_results"

    # Anthropic
    anthropic_api_key: str = ""


def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

**Step 5: Run test to verify it passes**

```bash
uv run pytest tests/test_core/test_config.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add .
git commit -m "feat(core): add configuration module with pydantic-settings"
```

---

### Task 4: Create Database Connection Module

**Files:**
- Create: `src/core/database.py`
- Test: `tests/test_core/test_database.py`

**Step 1: Write the failing test**

Create `tests/test_core/test_database.py`:

```python
import pytest
from sqlalchemy import text


def test_get_engine_returns_engine():
    """get_engine should return a SQLAlchemy engine."""
    from src.core.database import get_engine
    engine = get_engine()
    assert engine is not None
    assert hasattr(engine, "connect")


def test_get_session_factory_returns_sessionmaker():
    """get_session_factory should return a session factory."""
    from src.core.database import get_session_factory
    factory = get_session_factory()
    assert factory is not None
    assert callable(factory)


@pytest.mark.integration
def test_database_connection():
    """Should connect to the database successfully."""
    from src.core.database import get_engine
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_core/test_database.py -v -k "not integration"
```

Expected: FAIL with "cannot import name 'get_engine'"

**Step 3: Write minimal implementation**

Create `src/core/database.py`:

```python
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Get cached SQLAlchemy engine."""
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Get cached session factory."""
    return sessionmaker(
        bind=get_engine(),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def get_db() -> Session:
    """Dependency for FastAPI to get a database session."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_core/test_database.py -v -k "not integration"
```

Expected: PASS

**Step 5: Commit**

```bash
git add .
git commit -m "feat(core): add database connection module"
```

---

### Task 5: Create SQLAlchemy Base and Models

**Files:**
- Create: `src/models/__init__.py`
- Create: `src/models/base.py`
- Create: `src/models/patient.py`
- Create: `src/models/user.py`
- Create: `src/models/event.py`
- Test: `tests/test_models/__init__.py`
- Test: `tests/test_models/test_patient.py`

**Step 1: Create directory structure**

```bash
mkdir -p src/models tests/test_models
touch src/models/__init__.py tests/test_models/__init__.py
```

**Step 2: Write the failing test**

Create `tests/test_models/test_patient.py`:

```python
import uuid
from datetime import date


def test_patient_model_has_required_fields():
    """Patient model should have all required fields."""
    from src.models.patient import Patient

    patient = Patient(
        id=uuid.uuid4(),
        mrn="MRN001",
        first_name="John",
        last_name="Doe",
        date_of_birth=date(1980, 1, 15),
        gender="male",
        hospital_id="HOSP001",
    )

    assert patient.mrn == "MRN001"
    assert patient.first_name == "John"
    assert patient.last_name == "Doe"
    assert patient.gender == "male"


def test_lifecycle_phase_enum():
    """LifecyclePhase enum should have all phases."""
    from src.models.event import LifecyclePhase

    assert LifecyclePhase.CONSULTATION.value == "consultation"
    assert LifecyclePhase.PRE_SURGERY.value == "pre_surgery"
    assert LifecyclePhase.SURGERY.value == "surgery"
    assert LifecyclePhase.POST_SURGERY.value == "post_surgery"
    assert LifecyclePhase.FOLLOW_UP.value == "follow_up"
```

**Step 3: Run test to verify it fails**

```bash
uv run pytest tests/test_models/test_patient.py -v
```

Expected: FAIL with "cannot import name 'Patient'"

**Step 4: Create base model**

Create `src/models/base.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """Mixin that adds a UUID primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
```

**Step 5: Create Patient model**

Create `src/models/patient.py`:

```python
import uuid
from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class Patient(Base, UUIDMixin, TimestampMixin):
    """Patient entity representing a hospital patient."""

    __tablename__ = "patients"

    mrn: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    hospital_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Relationships
    events: Mapped[list["ClinicalEvent"]] = relationship(
        "ClinicalEvent",
        back_populates="patient",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Patient {self.mrn}: {self.first_name} {self.last_name}>"
```

**Step 6: Create User model**

Create `src/models/user.py`:

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, UUIDMixin


class UserRole:
    """User role constants."""

    UROLOGIST = "urologist"
    NURSE = "nurse"
    ADMIN = "admin"


class User(Base, UUIDMixin, TimestampMixin):
    """User entity for authentication and authorization."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.UROLOGIST, nullable=False)
    hospital_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"
```

**Step 7: Create Event models**

Create `src/models/event.py`:

```python
import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class LifecyclePhase(str, enum.Enum):
    """Patient lifecycle phases in urology care."""

    CONSULTATION = "consultation"
    PRE_SURGERY = "pre_surgery"
    SURGERY = "surgery"
    POST_SURGERY = "post_surgery"
    FOLLOW_UP = "follow_up"


class EventType(str, enum.Enum):
    """Types of clinical events."""

    LAB_RESULT = "lab_result"
    IMAGING = "imaging"
    PROCEDURE = "procedure"
    NOTE = "note"


class ExtractionStatus(str, enum.Enum):
    """Status of data extraction from uploaded files."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ClinicalEvent(Base, UUIDMixin, TimestampMixin):
    """Base clinical event in a patient's timeline."""

    __tablename__ = "clinical_events"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phase: Mapped[LifecyclePhase] = mapped_column(
        Enum(LifecyclePhase),
        nullable=False,
        index=True,
    )
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType),
        nullable=False,
        index=True,
    )
    event_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="events")

    # Polymorphic
    type: Mapped[str] = mapped_column(String(50))

    __mapper_args__ = {
        "polymorphic_on": "type",
        "polymorphic_identity": "clinical_event",
    }


class LabResult(ClinicalEvent):
    """Lab result with file and extracted data."""

    __tablename__ = "lab_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinical_events.id", ondelete="CASCADE"),
        primary_key=True,
    )

    original_file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # image, pdf
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        Enum(ExtractionStatus),
        default=ExtractionStatus.PENDING,
        nullable=False,
    )
    extracted_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    vector_embedding_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "lab_result",
    }


# Fix forward reference
from src.models.patient import Patient  # noqa: E402
```

**Step 8: Update models __init__.py**

Create `src/models/__init__.py`:

```python
from src.models.base import Base, TimestampMixin, UUIDMixin
from src.models.event import (
    ClinicalEvent,
    EventType,
    ExtractionStatus,
    LabResult,
    LifecyclePhase,
)
from src.models.patient import Patient
from src.models.user import User, UserRole

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "Patient",
    "User",
    "UserRole",
    "ClinicalEvent",
    "LabResult",
    "LifecyclePhase",
    "EventType",
    "ExtractionStatus",
]
```

**Step 9: Run test to verify it passes**

```bash
uv run pytest tests/test_models/test_patient.py -v
```

Expected: PASS

**Step 10: Commit**

```bash
git add .
git commit -m "feat(models): add Patient, User, ClinicalEvent, LabResult models"
```

---

### Task 6: Set Up Alembic Migrations

**Files:**
- Create: `alembic.ini`
- Create: `src/migrations/env.py`
- Create: `src/migrations/script.py.mako`
- Create: `src/migrations/versions/` (directory)

**Step 1: Initialize Alembic**

```bash
uv run alembic init src/migrations
```

**Step 2: Update alembic.ini**

Edit `alembic.ini` to set:

```ini
# line ~63
script_location = src/migrations

# line ~66
prepend_sys_path = .
```

**Step 3: Update migrations/env.py**

Replace `src/migrations/env.py` with:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from src.core.config import get_settings
from src.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Step 4: Create initial migration**

```bash
uv run alembic revision --autogenerate -m "initial_schema"
```

Expected: Creates a migration file in `src/migrations/versions/`

**Step 5: Run migrations**

```bash
uv run alembic upgrade head
```

Expected: Tables created in PostgreSQL

**Step 6: Verify tables exist**

```bash
docker exec -it urology-postgres psql -U urology -d urology_db -c "\dt"
```

Expected: Lists patients, users, clinical_events, lab_results, alembic_version tables

**Step 7: Commit**

```bash
git add .
git commit -m "feat(db): add alembic migrations with initial schema"
```

---

## Phase 2: API Foundation

### Task 7: Create Pydantic Schemas

**Files:**
- Create: `src/schemas/__init__.py`
- Create: `src/schemas/patient.py`
- Create: `src/schemas/user.py`
- Create: `src/schemas/event.py`
- Create: `src/schemas/auth.py`
- Test: `tests/test_schemas/__init__.py`
- Test: `tests/test_schemas/test_patient.py`

**Step 1: Create directory structure**

```bash
mkdir -p src/schemas tests/test_schemas
touch src/schemas/__init__.py tests/test_schemas/__init__.py
```

**Step 2: Write the failing test**

Create `tests/test_schemas/test_patient.py`:

```python
import uuid
from datetime import date

import pytest
from pydantic import ValidationError


def test_patient_create_schema_validates():
    """PatientCreate should validate required fields."""
    from src.schemas.patient import PatientCreate

    patient = PatientCreate(
        mrn="MRN001",
        first_name="John",
        last_name="Doe",
        date_of_birth=date(1980, 1, 15),
        gender="male",
        hospital_id="HOSP001",
    )
    assert patient.mrn == "MRN001"


def test_patient_create_rejects_empty_mrn():
    """PatientCreate should reject empty MRN."""
    from src.schemas.patient import PatientCreate

    with pytest.raises(ValidationError):
        PatientCreate(
            mrn="",
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1980, 1, 15),
            gender="male",
            hospital_id="HOSP001",
        )


def test_patient_response_schema():
    """PatientResponse should include id and timestamps."""
    from src.schemas.patient import PatientResponse
    from datetime import datetime

    patient = PatientResponse(
        id=uuid.uuid4(),
        mrn="MRN001",
        first_name="John",
        last_name="Doe",
        date_of_birth=date(1980, 1, 15),
        gender="male",
        hospital_id="HOSP001",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    assert patient.id is not None
```

**Step 3: Run test to verify it fails**

```bash
uv run pytest tests/test_schemas/test_patient.py -v
```

Expected: FAIL with "cannot import name 'PatientCreate'"

**Step 4: Create patient schemas**

Create `src/schemas/patient.py`:

```python
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PatientBase(BaseModel):
    """Base patient schema with common fields."""

    mrn: str = Field(..., min_length=1, max_length=50, description="Medical Record Number")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    gender: str = Field(..., pattern="^(male|female|other)$")
    hospital_id: str = Field(..., min_length=1, max_length=50)


class PatientCreate(PatientBase):
    """Schema for creating a new patient."""

    pass


class PatientUpdate(BaseModel):
    """Schema for updating a patient."""

    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    gender: str | None = Field(None, pattern="^(male|female|other)$")


class PatientResponse(PatientBase):
    """Schema for patient response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PatientWithTimeline(PatientResponse):
    """Patient with their clinical events."""

    events: list["ClinicalEventResponse"] = []


# Forward reference resolved at runtime
from src.schemas.event import ClinicalEventResponse  # noqa: E402

PatientWithTimeline.model_rebuild()
```

**Step 5: Create user schemas**

Create `src/schemas/user.py`:

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema."""

    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    role: str = Field(default="urologist", pattern="^(urologist|nurse|admin)$")
    hospital_id: str = Field(..., min_length=1, max_length=50)


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    """Schema for user response (no password)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

**Step 6: Create auth schemas**

Create `src/schemas/auth.py`:

```python
from pydantic import BaseModel


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # user_id
    exp: int


class LoginRequest(BaseModel):
    """Login request body."""

    username: str
    password: str
```

**Step 7: Create event schemas**

Create `src/schemas/event.py`:

```python
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.models.event import EventType, ExtractionStatus, LifecyclePhase


class ClinicalEventBase(BaseModel):
    """Base clinical event schema."""

    phase: LifecyclePhase
    event_type: EventType
    event_date: datetime
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class ClinicalEventCreate(ClinicalEventBase):
    """Schema for creating a clinical event."""

    patient_id: uuid.UUID


class ClinicalEventResponse(ClinicalEventBase):
    """Schema for clinical event response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    uploaded_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class LabResultResponse(ClinicalEventResponse):
    """Schema for lab result response."""

    original_file_path: str
    file_type: str
    extraction_status: ExtractionStatus
    extracted_data: dict[str, Any] | None
    extraction_confidence: float | None


class LabResultUpload(BaseModel):
    """Schema for uploading a lab result."""

    patient_id: uuid.UUID
    phase: LifecyclePhase
    event_date: datetime
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
```

**Step 8: Update schemas __init__.py**

Create `src/schemas/__init__.py`:

```python
from src.schemas.auth import LoginRequest, Token, TokenPayload
from src.schemas.event import (
    ClinicalEventCreate,
    ClinicalEventResponse,
    LabResultResponse,
    LabResultUpload,
)
from src.schemas.patient import (
    PatientCreate,
    PatientResponse,
    PatientUpdate,
    PatientWithTimeline,
)
from src.schemas.user import UserCreate, UserResponse

__all__ = [
    "PatientCreate",
    "PatientUpdate",
    "PatientResponse",
    "PatientWithTimeline",
    "UserCreate",
    "UserResponse",
    "Token",
    "TokenPayload",
    "LoginRequest",
    "ClinicalEventCreate",
    "ClinicalEventResponse",
    "LabResultResponse",
    "LabResultUpload",
]
```

**Step 9: Run test to verify it passes**

```bash
uv run pytest tests/test_schemas/test_patient.py -v
```

Expected: PASS

**Step 10: Commit**

```bash
git add .
git commit -m "feat(schemas): add Pydantic schemas for patient, user, event, auth"
```

---

### Task 8: Create Security Module (JWT + Password Hashing)

**Files:**
- Create: `src/core/security.py`
- Test: `tests/test_core/test_security.py`

**Step 1: Write the failing test**

Create `tests/test_core/test_security.py`:

```python
from datetime import timedelta


def test_password_hashing():
    """Passwords should be hashed and verifiable."""
    from src.core.security import hash_password, verify_password

    password = "secret123"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_access_token():
    """Should create a valid JWT token."""
    from src.core.security import create_access_token, decode_access_token

    token = create_access_token(subject="user123", expires_delta=timedelta(hours=1))

    assert token is not None
    payload = decode_access_token(token)
    assert payload is not None
    assert payload.sub == "user123"


def test_decode_invalid_token():
    """Should return None for invalid tokens."""
    from src.core.security import decode_access_token

    payload = decode_access_token("invalid.token.here")
    assert payload is None
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_core/test_security.py -v
```

Expected: FAIL with "cannot import name 'hash_password'"

**Step 3: Write minimal implementation**

Create `src/core/security.py`:

```python
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import get_settings
from src.schemas.auth import TokenPayload

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    settings = get_settings()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> TokenPayload | None:
    """Decode and validate a JWT access token."""
    settings = get_settings()

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return TokenPayload(sub=payload["sub"], exp=payload["exp"])
    except JWTError:
        return None
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_core/test_security.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add .
git commit -m "feat(core): add security module with JWT and password hashing"
```

---

### Task 9: Create FastAPI Application and Auth Router

**Files:**
- Create: `src/main.py`
- Create: `src/api/__init__.py`
- Create: `src/api/deps.py`
- Create: `src/api/auth.py`
- Test: `tests/test_api/__init__.py`
- Test: `tests/test_api/test_auth.py`

**Step 1: Create directory structure**

```bash
mkdir -p src/api tests/test_api
touch src/api/__init__.py tests/test_api/__init__.py
```

**Step 2: Write the failing test**

Create `tests/test_api/test_auth.py`:

```python
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from src.main import app
    return TestClient(app)


def test_register_user(client):
    """Should register a new user."""
    response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
            "role": "urologist",
            "hospital_id": "HOSP001",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert "password" not in data


def test_login(client):
    """Should login and return a token."""
    # First register
    client.post(
        "/api/auth/register",
        json={
            "username": "logintest",
            "email": "login@example.com",
            "password": "password123",
            "role": "urologist",
            "hospital_id": "HOSP001",
        },
    )

    # Then login
    response = client.post(
        "/api/auth/login",
        json={"username": "logintest", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
```

**Step 3: Run test to verify it fails**

```bash
uv run pytest tests/test_api/test_auth.py -v
```

Expected: FAIL with "cannot import name 'app'"

**Step 4: Create dependencies**

Create `src/api/deps.py`:

```python
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import decode_access_token
from src.models import User

security = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Get the current authenticated user from the JWT token."""
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.query(User).filter(User.id == payload.sub).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]
```

**Step 5: Create auth router**

Create `src/api/auth.py`:

```python
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import DbSession
from src.core.security import create_access_token, hash_password, verify_password
from src.models import User
from src.schemas import LoginRequest, Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: DbSession) -> User:
    """Register a new user."""
    # Check if username exists
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check if email exists
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role=user_in.role,
        hospital_id=user_in.hospital_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=Token)
def login(login_in: LoginRequest, db: DbSession) -> Token:
    """Login and get an access token."""
    user = db.query(User).filter(User.username == login_in.username).first()

    if not user or not verify_password(login_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    access_token = create_access_token(subject=str(user.id))

    return Token(access_token=access_token)
```

**Step 6: Create main application**

Create `src/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import router as auth_router

app = FastAPI(
    title="Urology Data Platform",
    description="Multi-modal patient data platform for urology",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")


@app.get("/health")
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}
```

**Step 7: Create test fixtures**

Create `tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.database import get_db
from src.main import app
from src.models import Base


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

**Step 8: Update test_auth.py to use fixtures**

Update `tests/test_api/test_auth.py`:

```python
def test_register_user(client):
    """Should register a new user."""
    response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
            "role": "urologist",
            "hospital_id": "HOSP001",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_username(client):
    """Should reject duplicate usernames."""
    user_data = {
        "username": "duplicate",
        "email": "dup1@example.com",
        "password": "password123",
        "role": "urologist",
        "hospital_id": "HOSP001",
    }
    client.post("/api/auth/register", json=user_data)

    user_data["email"] = "dup2@example.com"
    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code == 400


def test_login(client):
    """Should login and return a token."""
    # First register
    client.post(
        "/api/auth/register",
        json={
            "username": "logintest",
            "email": "login@example.com",
            "password": "password123",
            "role": "urologist",
            "hospital_id": "HOSP001",
        },
    )

    # Then login
    response = client.post(
        "/api/auth/login",
        json={"username": "logintest", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    """Should reject wrong password."""
    # First register
    client.post(
        "/api/auth/register",
        json={
            "username": "wrongpw",
            "email": "wrongpw@example.com",
            "password": "password123",
            "role": "urologist",
            "hospital_id": "HOSP001",
        },
    )

    # Try wrong password
    response = client.post(
        "/api/auth/login",
        json={"username": "wrongpw", "password": "wrongpassword"},
    )
    assert response.status_code == 401
```

**Step 9: Run tests to verify they pass**

```bash
uv run pytest tests/test_api/test_auth.py -v
```

Expected: PASS

**Step 10: Commit**

```bash
git add .
git commit -m "feat(api): add FastAPI app with auth endpoints"
```

---

### Task 10: Create Patient API Router

**Files:**
- Create: `src/api/patients.py`
- Test: `tests/test_api/test_patients.py`

**Step 1: Write the failing test**

Create `tests/test_api/test_patients.py`:

```python
import uuid


def create_auth_header(client) -> dict:
    """Helper to create authenticated header."""
    client.post(
        "/api/auth/register",
        json={
            "username": "testdoc",
            "email": "doc@example.com",
            "password": "password123",
            "role": "urologist",
            "hospital_id": "HOSP001",
        },
    )
    response = client.post(
        "/api/auth/login",
        json={"username": "testdoc", "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_patient(client):
    """Should create a new patient."""
    headers = create_auth_header(client)

    response = client.post(
        "/api/patients",
        headers=headers,
        json={
            "mrn": "MRN001",
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1980-01-15",
            "gender": "male",
            "hospital_id": "HOSP001",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["mrn"] == "MRN001"
    assert "id" in data


def test_get_patient(client):
    """Should get a patient by ID."""
    headers = create_auth_header(client)

    # Create patient
    create_response = client.post(
        "/api/patients",
        headers=headers,
        json={
            "mrn": "MRN002",
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "1985-05-20",
            "gender": "female",
            "hospital_id": "HOSP001",
        },
    )
    patient_id = create_response.json()["id"]

    # Get patient
    response = client.get(f"/api/patients/{patient_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["mrn"] == "MRN002"


def test_list_patients(client):
    """Should list patients with pagination."""
    headers = create_auth_header(client)

    # Create two patients
    for i in range(2):
        client.post(
            "/api/patients",
            headers=headers,
            json={
                "mrn": f"MRN10{i}",
                "first_name": f"Patient{i}",
                "last_name": "Test",
                "date_of_birth": "1990-01-01",
                "gender": "male",
                "hospital_id": "HOSP001",
            },
        )

    response = client.get("/api/patients", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_create_patient_requires_auth(client):
    """Should require authentication to create patient."""
    response = client.post(
        "/api/patients",
        json={
            "mrn": "MRN999",
            "first_name": "No",
            "last_name": "Auth",
            "date_of_birth": "1990-01-01",
            "gender": "male",
            "hospital_id": "HOSP001",
        },
    )
    assert response.status_code == 403  # No auth header
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_api/test_patients.py -v
```

Expected: FAIL with 404 (route doesn't exist)

**Step 3: Write minimal implementation**

Create `src/api/patients.py`:

```python
import uuid

from fastapi import APIRouter, HTTPException, Query, status

from src.api.deps import CurrentUser, DbSession
from src.models import Patient
from src.schemas import PatientCreate, PatientResponse, PatientUpdate, PatientWithTimeline

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    patient_in: PatientCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> Patient:
    """Create a new patient."""
    # Check if MRN exists
    if db.query(Patient).filter(Patient.mrn == patient_in.mrn).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient with this MRN already exists",
        )

    patient = Patient(**patient_in.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)

    return patient


@router.get("", response_model=list[PatientResponse])
def list_patients(
    db: DbSession,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    hospital_id: str | None = None,
) -> list[Patient]:
    """List patients with optional filtering."""
    query = db.query(Patient)

    if hospital_id:
        query = query.filter(Patient.hospital_id == hospital_id)

    return query.offset(skip).limit(limit).all()


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> Patient:
    """Get a patient by ID."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    return patient


@router.get("/{patient_id}/timeline", response_model=PatientWithTimeline)
def get_patient_timeline(
    patient_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> Patient:
    """Get a patient with their clinical timeline."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    return patient


@router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: uuid.UUID,
    patient_in: PatientUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Patient:
    """Update a patient."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    update_data = patient_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)

    return patient
```

**Step 4: Update main.py to include router**

Edit `src/main.py` to add:

```python
from src.api.patients import router as patients_router

# Add after auth_router
app.include_router(patients_router, prefix="/api")
```

**Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_api/test_patients.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add .
git commit -m "feat(api): add patient CRUD endpoints"
```

---

## Phase 3: Upload & Extraction (Tasks 11-17)

Due to length constraints, I'll summarize the remaining tasks. Each follows the same TDD pattern.

### Task 11: Create File Storage Service (MinIO)

**Files:** `src/services/storage.py`, `tests/test_services/test_storage.py`

- `upload_file(file_path, content)` → stores file in MinIO
- `download_file(file_path)` → retrieves file content
- `delete_file(file_path)` → removes file

### Task 12: Create Upload Endpoint

**Files:** `src/api/upload.py`, `tests/test_api/test_upload.py`

- `POST /api/upload/lab-result` accepts multipart file + metadata
- Stores file in MinIO, creates LabResult record with `pending` status

### Task 13: Create PDF Text Extraction Service

**Files:** `src/services/extraction/pdf_extractor.py`, `tests/test_services/test_pdf_extractor.py`

- `is_text_pdf(file_bytes)` → True if PDF has extractable text
- `extract_lab_values(file_bytes)` → returns structured JSON of lab values

### Task 14: Create VLM Extraction Service

**Files:** `src/services/extraction/vlm_extractor.py`, `tests/test_services/test_vlm_extractor.py`

- `extract_lab_values_from_image(image_bytes)` → calls Claude Vision API
- Returns structured JSON matching the lab values schema

### Task 15: Create Extraction Router

**Files:** `src/services/extraction/router.py`, `tests/test_services/test_extraction_router.py`

- `process_lab_result(lab_result_id)` → routes to PDF or VLM based on file type
- Updates LabResult with extracted data and status

### Task 16: Create Background Worker

**Files:** `src/workers/extraction_worker.py`

- Uses FastAPI BackgroundTasks to process uploads
- Updates extraction_status through the pipeline

### Task 17: Create Reprocess Endpoint

**Files:** Add to `src/api/upload.py`

- `POST /api/lab-results/{id}/reprocess` → re-triggers extraction

---

## Phase 4: Vector Search & Summary (Tasks 18-22)

### Task 18: Create Milvus Collection Schema

**Files:** `src/services/embedding.py`, `tests/test_services/test_embedding.py`

- `init_collection()` → creates Milvus collection with correct schema
- `insert_embedding(id, vector, metadata)`
- `search_similar(query_vector, limit)`

### Task 19: Create Embedding Generation

**Files:** `src/services/embedding.py`

- `generate_embedding(text)` → calls OpenAI/Voyage embeddings API
- Returns vector for storage

### Task 20: Update Extraction Pipeline for Embeddings

**Files:** Update `src/services/extraction/router.py`

- After extraction, generate embedding and store in Milvus

### Task 21: Create Search Endpoint

**Files:** `src/api/search.py`, `tests/test_api/test_search.py`

- `GET /api/search?q=...` → semantic search across lab results
- Returns matching patients with relevant events

### Task 22: Create Summary Generation Service

**Files:** `src/services/summary.py`, `tests/test_services/test_summary.py`

- `generate_patient_summary(patient_id)` → calls Claude to summarize timeline
- `GET /api/patients/{id}/summary` endpoint

---

## Phase 5: Streamlit UI (Tasks 23-28)

### Task 23: Create Streamlit App Structure

**Files:** `ui/app.py`, `ui/utils/api.py`, `ui/utils/auth.py`

- Multi-page app structure
- API client helper with auth token management

### Task 24: Create Patient Search Page

**Files:** `ui/pages/1_patient_search.py`

- Search input, filters
- Patient cards with quick preview

### Task 25: Create Patient Timeline Page

**Files:** `ui/pages/2_patient_timeline.py`

- Vertical timeline by lifecycle phase
- AI summary panel at top

### Task 26: Create Lab Result Detail Page

**Files:** `ui/pages/3_lab_detail.py`

- Side-by-side original + extracted data
- Trend chart for values

### Task 27: Create Upload Page

**Files:** `ui/pages/4_upload.py`

- Drag-drop zone
- Patient + phase selection
- Processing status

### Task 28: Add Login/Auth Flow

**Files:** `ui/components/auth.py`

- Login form in sidebar
- Session state management

---

## Phase 6: Polish & Testing (Tasks 29-32)

### Task 29: Add Comprehensive Error Handling

- Global exception handler
- Structured error responses
- Logging configuration

### Task 30: Write Integration Tests

- End-to-end upload → extraction → search flow
- Docker-based test environment

### Task 31: Add Logging and Monitoring

- Structured logging with structlog
- Request ID tracking
- Basic metrics endpoint

### Task 32: Create Deployment Documentation

- Docker production configuration
- Environment variable documentation
- Backup and restore procedures

---

## Verification Checklist

After completing all tasks, verify:

1. [ ] `docker compose up -d` starts all services
2. [ ] `uv run alembic upgrade head` creates tables
3. [ ] `uv run uvicorn src.main:app --reload` starts API
4. [ ] `uv run streamlit run ui/app.py` starts UI
5. [ ] Can register and login via UI
6. [ ] Can create a patient
7. [ ] Can upload a lab result image
8. [ ] Extraction completes and shows data
9. [ ] Timeline shows uploaded events
10. [ ] Patient summary generates
11. [ ] Search finds patients by lab values
12. [ ] `uv run pytest` passes all tests
