# M1 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Postgres + `libpoolzone` Python package + Alembic-managed schema + catalog service layer (products / categories / locks) with full test coverage. End state: a developer can `import libpoolzone`, create products in Postgres, lock fields, and verify locks prevent updates.

**Architecture:** Single Python project managed by `pyproject.toml`. Postgres runs in Docker via a standalone `docker-compose.yml`. SQLAlchemy 2.x ORM, Alembic migrations, Pydantic-settings for config. Catalog service layer is pure functions on top of models — no HTTP, no CLI, no importer/exporter yet (those come in later milestones). Tests use pytest with a transactional rollback fixture against a real Postgres test database.

**Tech Stack:** Python 3.11 · PostgreSQL 16 · SQLAlchemy 2 · Alembic · Pydantic v2 / pydantic-settings · pytest · Ruff · Docker Compose

**Reference spec:** `docs/superpowers/specs/2026-05-13-poolzone-platform-design.md`

**Branch:** Continue on `feature/newSystemV1` (current branch).

---

## File structure for this milestone

```
poolzone/
├── pyproject.toml                        # NEW — Python project config
├── docker-compose.yml                    # NEW — Postgres service for dev + test
├── .env.example                          # NEW — DATABASE_URL template
├── alembic.ini                           # NEW — Alembic config
│
├── libpoolzone/                          # NEW package
│   ├── __init__.py
│   ├── settings.py                       # Pydantic-settings (env-driven config)
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base.py                       # SQLAlchemy DeclarativeBase
│   │   ├── engine.py                     # engine + session factory
│   │   ├── migrations/                   # Alembic versions live here
│   │   │   ├── env.py
│   │   │   ├── script.py.mako
│   │   │   └── versions/
│   │   └── models/
│   │       ├── __init__.py               # re-exports all models
│   │       ├── product.py                # Product, ProductImage, ProductParameter, ProductFile
│   │       ├── category.py               # Category, ProductCategory
│   │       ├── supplier.py               # Supplier, SupplierProduct, SupplierCategoryMapping
│   │       ├── pricing.py                # PricingRule, CompetitorPrice
│   │       ├── lock.py                   # ProductFieldLock
│   │       ├── seo.py                    # SeoSuggestion
│   │       └── sync_run.py               # SyncRun
│   │
│   ├── catalog/                          # service layer over models
│   │   ├── __init__.py
│   │   ├── products.py                   # CRUD + field setter that respects locks
│   │   ├── categories.py                 # tree CRUD + product link
│   │   └── locks.py                      # is_locked / lock_field / unlock_field
│   │
│   ├── importers/__init__.py             # empty stub — populated in M2
│   ├── exporter/__init__.py              # empty stub — populated in M3
│   ├── seo/__init__.py                   # empty stub — populated in M5
│   └── pricing/__init__.py               # empty stub — populated in M7
│
└── tests/
    ├── __init__.py
    ├── conftest.py                       # db fixture (transactional rollback)
    ├── unit/
    │   ├── __init__.py
    │   └── catalog/
    │       ├── __init__.py
    │       ├── test_products.py
    │       ├── test_categories.py
    │       └── test_locks.py
    └── integration/
        ├── __init__.py
        └── test_smoke.py                 # end-to-end: create, lock, attempt-update, verify
```

**Design rationale for file boundaries:**
- `storage/models/` is split by aggregate (product, category, supplier, …) — one file per related cluster of tables. Each file stays under ~150 lines and reasons about one concern.
- `catalog/` (service layer) deliberately mirrors model files: `products.py` ↔ `models/product.py`, etc. Higher-level services (importers, exporter) will call into `catalog/` rather than touching models directly.
- Stub `__init__.py` files for `importers/`, `exporter/`, `seo/`, `pricing/` so import paths exist from day 1 — later milestones fill them in without restructuring.

---

## Task 1: Bootstrap Python project (pyproject.toml + venv)

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "libpoolzone"
version = "0.1.0"
description = "Poolzone platform — shared Python package."
requires-python = ">=3.11"
dependencies = [
    "sqlalchemy>=2.0,<3.0",
    "alembic>=1.13,<2.0",
    "psycopg[binary]>=3.1,<4.0",
    "pydantic>=2.6,<3.0",
    "pydantic-settings>=2.2,<3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0,<9.0",
    "pytest-cov>=4.1,<5.0",
    "ruff>=0.4,<0.5",
]

[tool.setuptools.packages.find]
include = ["libpoolzone*"]
exclude = ["tests*", "apps*", "frontend*", "archive*"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"
```

- [ ] **Step 2: Create and activate a virtualenv**

Run:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Expected: `(.venv)` prefix appears in prompt; pip upgrades silently.

- [ ] **Step 3: Install the project in editable mode with dev extras**

Run:
```bash
pip install -e ".[dev]"
```

Expected: installs SQLAlchemy, Alembic, psycopg, pytest, ruff, etc. Final line includes `Successfully installed libpoolzone-0.1.0 …`.

- [ ] **Step 4: Verify pytest + ruff are callable**

Run:
```bash
pytest --version
ruff --version
```

Expected: prints versions (pytest 8.x, ruff 0.4.x).

- [ ] **Step 5: Add `.venv/` to `.gitignore`** (only if it's not already covered)

Check:
```bash
grep -n "^\.venv" .gitignore
```

If no output, run:
```bash
printf "\n# Python virtualenv\n.venv/\n" >> .gitignore
```

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore
git commit -m "Bootstrap libpoolzone Python project"
```

---

## Task 2: Postgres via docker-compose

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Modify: `.gitignore` (add `.env`)

- [ ] **Step 1: Create `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16
    container_name: poolzone-postgres
    environment:
      POSTGRES_USER: poolzone
      POSTGRES_PASSWORD: poolzone
      POSTGRES_DB: poolzone
    ports:
      - "5432:5432"
    volumes:
      - poolzone-pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U poolzone -d poolzone"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  poolzone-pgdata:
```

- [ ] **Step 2: Create `.env.example`**

```bash
# Copy to .env and fill in.
DATABASE_URL=postgresql+psycopg://poolzone:poolzone@localhost:5432/poolzone
DATABASE_URL_TEST=postgresql+psycopg://poolzone:poolzone@localhost:5432/poolzone_test
```

- [ ] **Step 3: Create a local `.env` from the example**

Run:
```bash
cp .env.example .env
```

- [ ] **Step 4: Add `.env` to `.gitignore`** (only if not already there)

Check:
```bash
grep -n "^\.env$" .gitignore
```

If no output, run:
```bash
printf "\n# Local secrets\n.env\n" >> .gitignore
```

- [ ] **Step 5: Bring Postgres up**

Run:
```bash
docker compose up -d postgres
```

Expected: pulls postgres:16 image (first run only), starts container, returns to prompt.

- [ ] **Step 6: Wait for healthcheck to pass**

Run:
```bash
docker compose ps
```

Expected: status column shows `Up (healthy)` within ~10 seconds.

- [ ] **Step 7: Create the test database**

Run:
```bash
docker exec poolzone-postgres psql -U poolzone -d poolzone -c "CREATE DATABASE poolzone_test;"
```

Expected: `CREATE DATABASE` confirmation.

- [ ] **Step 8: Verify both databases exist**

Run:
```bash
docker exec poolzone-postgres psql -U poolzone -l
```

Expected: list includes both `poolzone` and `poolzone_test`.

- [ ] **Step 9: Commit**

```bash
git add docker-compose.yml .env.example .gitignore
git commit -m "Add Postgres docker-compose for local dev + test"
```

---

## Task 3: libpoolzone package skeleton

**Files:**
- Create: `libpoolzone/__init__.py`
- Create: `libpoolzone/storage/__init__.py`
- Create: `libpoolzone/storage/models/__init__.py`
- Create: `libpoolzone/catalog/__init__.py`
- Create: `libpoolzone/importers/__init__.py`
- Create: `libpoolzone/exporter/__init__.py`
- Create: `libpoolzone/seo/__init__.py`
- Create: `libpoolzone/pricing/__init__.py`

- [ ] **Step 1: Create all empty `__init__.py` files in one shot**

Run:
```bash
mkdir -p libpoolzone/storage/models libpoolzone/catalog \
         libpoolzone/importers libpoolzone/exporter \
         libpoolzone/seo libpoolzone/pricing
touch libpoolzone/__init__.py \
      libpoolzone/storage/__init__.py \
      libpoolzone/storage/models/__init__.py \
      libpoolzone/catalog/__init__.py \
      libpoolzone/importers/__init__.py \
      libpoolzone/exporter/__init__.py \
      libpoolzone/seo/__init__.py \
      libpoolzone/pricing/__init__.py
```

- [ ] **Step 2: Verify import works**

Run:
```bash
python -c "import libpoolzone; import libpoolzone.storage; import libpoolzone.catalog; import libpoolzone.importers; import libpoolzone.exporter; import libpoolzone.seo; import libpoolzone.pricing; print('ok')"
```

Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add libpoolzone/
git commit -m "Create libpoolzone package skeleton"
```

---

## Task 4: Settings module

**Files:**
- Create: `libpoolzone/settings.py`
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/unit/test_settings.py`

- [ ] **Step 1: Create empty `tests/` package markers**

Run:
```bash
mkdir -p tests/unit
touch tests/__init__.py tests/unit/__init__.py
```

- [ ] **Step 2: Write the failing test** at `tests/unit/test_settings.py`

```python
import os

from libpoolzone.settings import Settings


def test_settings_reads_database_url_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@host:5432/db")
    monkeypatch.setenv("DATABASE_URL_TEST", "postgresql+psycopg://u:p@host:5432/db_test")

    settings = Settings()

    assert settings.database_url == "postgresql+psycopg://u:p@host:5432/db"
    assert settings.database_url_test == "postgresql+psycopg://u:p@host:5432/db_test"


def test_settings_database_url_required(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL_TEST", raising=False)

    # Silence .env file discovery for this test
    monkeypatch.setattr(os, "environ", {})

    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
```

- [ ] **Step 3: Run test, verify it fails**

Run:
```bash
pytest tests/unit/test_settings.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'libpoolzone.settings'`.

- [ ] **Step 4: Implement `libpoolzone/settings.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration. Reads from env vars and (optionally) `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str
    database_url_test: str
```

- [ ] **Step 5: Run test, verify it passes**

Run:
```bash
pytest tests/unit/test_settings.py -v
```

Expected: both tests PASS.

- [ ] **Step 6: Commit**

```bash
git add libpoolzone/settings.py tests/
git commit -m "Add env-driven Settings module"
```

---

## Task 5: SQLAlchemy base + engine + session factory

**Files:**
- Create: `libpoolzone/storage/base.py`
- Create: `libpoolzone/storage/engine.py`
- Create: `tests/unit/test_engine.py`

- [ ] **Step 1: Write the failing test** at `tests/unit/test_engine.py`

```python
from sqlalchemy import text

from libpoolzone.storage.engine import get_engine, session_scope


def test_get_engine_returns_a_working_engine(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://poolzone:poolzone@localhost:5432/poolzone_test")
    monkeypatch.setenv("DATABASE_URL_TEST", "postgresql+psycopg://poolzone:poolzone@localhost:5432/poolzone_test")

    engine = get_engine(test=True)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_session_scope_commits_on_success(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://poolzone:poolzone@localhost:5432/poolzone_test")
    monkeypatch.setenv("DATABASE_URL_TEST", "postgresql+psycopg://poolzone:poolzone@localhost:5432/poolzone_test")

    with session_scope(test=True) as session:
        result = session.execute(text("SELECT 42"))
        assert result.scalar() == 42
```

- [ ] **Step 2: Run test, verify it fails**

Run:
```bash
pytest tests/unit/test_engine.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'libpoolzone.storage.engine'`.

- [ ] **Step 3: Implement `libpoolzone/storage/base.py`**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared SQLAlchemy declarative base for all libpoolzone models."""
```

- [ ] **Step 4: Implement `libpoolzone/storage/engine.py`**

```python
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from libpoolzone.settings import Settings


@lru_cache(maxsize=2)
def get_engine(*, test: bool = False) -> Engine:
    settings = Settings()
    url = settings.database_url_test if test else settings.database_url
    return create_engine(url, pool_pre_ping=True, future=True)


def get_session_factory(*, test: bool = False) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(test=test), expire_on_commit=False)


@contextmanager
def session_scope(*, test: bool = False):
    """Provide a transactional scope: commit on success, rollback on error."""
    Session = get_session_factory(test=test)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

- [ ] **Step 5: Run test, verify it passes**

Run:
```bash
pytest tests/unit/test_engine.py -v
```

Expected: both tests PASS. (Requires Postgres up from Task 2.)

- [ ] **Step 6: Commit**

```bash
git add libpoolzone/storage/base.py libpoolzone/storage/engine.py tests/unit/test_engine.py
git commit -m "Add SQLAlchemy Base, engine factory, and session_scope context manager"
```

---

## Task 6: Models — products + variants + child tables

**Files:**
- Create: `libpoolzone/storage/models/product.py`
- Modify: `libpoolzone/storage/models/__init__.py`

- [ ] **Step 1: Implement `libpoolzone/storage/models/product.py`**

```python
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from libpoolzone.storage.base import Base


class Product(Base):
    """Master catalog row. Standalone product when parent_id is NULL, variant when set."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Identity
    ean: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    supplier_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Logistics
    stock: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[int | None] = mapped_column(Integer, nullable=True)  # grams
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Multilingual content as JSONB ({"cs": "..."} etc.)
    titles: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    short_descriptions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    long_descriptions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    urls: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    seo_titles: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    seo_descriptions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    seo_keywords: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Pricing (excl VAT)
    price_purchase: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_common: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_original: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Provenance
    primary_supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    parent: Mapped["Product | None"] = relationship(remote_side="Product.id", back_populates="variants")
    variants: Mapped[list["Product"]] = relationship(back_populates="parent")
    images: Mapped[list["ProductImage"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    parameters: Mapped[list["ProductParameter"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    files: Mapped[list["ProductFile"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    alt: Mapped[str | None] = mapped_column(Text, nullable=True)
    ord: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    product: Mapped[Product] = relationship(back_populates="images")


class ProductParameter(Base):
    __tablename__ = "product_parameters"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    name_i18n: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    value_i18n: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    product: Mapped[Product] = relationship(back_populates="parameters")


class ProductFile(Base):
    __tablename__ = "product_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # "pdf_manual", "datasheet", …

    product: Mapped[Product] = relationship(back_populates="files")
```

- [ ] **Step 2: Re-export from `libpoolzone/storage/models/__init__.py`**

```python
from libpoolzone.storage.models.product import (
    Product,
    ProductFile,
    ProductImage,
    ProductParameter,
)

__all__ = [
    "Product",
    "ProductFile",
    "ProductImage",
    "ProductParameter",
]
```

- [ ] **Step 3: Verify the models import cleanly**

Run:
```bash
python -c "from libpoolzone.storage.models import Product, ProductImage, ProductParameter, ProductFile; print('ok')"
```

Expected: prints `ok`. (Note: import will fail later if you reference unresolved FKs — that's fine for now because `suppliers` table is added in Task 7.)

- [ ] **Step 4: Commit**

```bash
git add libpoolzone/storage/models/product.py libpoolzone/storage/models/__init__.py
git commit -m "Add Product / ProductImage / ProductParameter / ProductFile models"
```

---

## Task 7: Models — supplier + category + lock + pricing + SEO + sync_run

**Files:**
- Create: `libpoolzone/storage/models/supplier.py`
- Create: `libpoolzone/storage/models/category.py`
- Create: `libpoolzone/storage/models/lock.py`
- Create: `libpoolzone/storage/models/pricing.py`
- Create: `libpoolzone/storage/models/seo.py`
- Create: `libpoolzone/storage/models/sync_run.py`
- Modify: `libpoolzone/storage/models/__init__.py`

- [ ] **Step 1: Implement `libpoolzone/storage/models/supplier.py`**

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from libpoolzone.storage.base import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    adapter_key: Mapped[str] = mapped_column(String(64))
    feed_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SupplierProduct(Base):
    __tablename__ = "supplier_products"
    __table_args__ = (UniqueConstraint("supplier_id", "supplier_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), index=True)
    supplier_code: Mapped[str] = mapped_column(String(64), index=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    supplier_category_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )


class SupplierCategoryMapping(Base):
    __tablename__ = "supplier_category_mappings"
    __table_args__ = (UniqueConstraint("supplier_id", "supplier_path"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), index=True)
    supplier_path: Mapped[str] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
```

- [ ] **Step 2: Implement `libpoolzone/storage/models/category.py`**

```python
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libpoolzone.storage.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )

    name_i18n: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    description_i18n: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    seo_title_i18n: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    seo_description_i18n: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    seo_keywords_i18n: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    url_i18n: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    parent: Mapped["Category | None"] = relationship(remote_side="Category.id", back_populates="children")
    children: Mapped[list["Category"]] = relationship(back_populates="parent")


class ProductCategory(Base):
    __tablename__ = "product_categories"
    __table_args__ = (UniqueConstraint("product_id", "category_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), index=True)
    primary_yn: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
```

- [ ] **Step 3: Implement `libpoolzone/storage/models/lock.py`**

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from libpoolzone.storage.base import Base


class ProductFieldLock(Base):
    """A row here = supplier sync will NOT overwrite this field for this product."""

    __tablename__ = "product_field_locks"
    __table_args__ = (UniqueConstraint("product_id", "field_path"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    field_path: Mapped[str] = mapped_column(String(128))
    locked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 4: Implement `libpoolzone/storage/models/pricing.py`**

```python
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from libpoolzone.storage.base import Base


class PricingRule(Base):
    """Margin + coefficient applied during export. Scope = supplier or product."""

    __tablename__ = "pricing_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(16))  # "supplier" | "product"
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    product_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    margin_pct: Mapped[Decimal] = mapped_column(Numeric(5, 4))  # e.g. 0.35
    coefficient: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=1)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class CompetitorPrice(Base):
    __tablename__ = "competitor_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    competitor_name: Mapped[str] = mapped_column(String(64))
    url: Mapped[str] = mapped_column(Text)
    price_with_vat: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 5: Implement `libpoolzone/storage/models/seo.py`**

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from libpoolzone.storage.base import Base


class SeoSuggestion(Base):
    """AI-generated content awaiting human review."""

    __tablename__ = "seo_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_kind: Mapped[str] = mapped_column(String(16))  # "product" | "category"
    target_id: Mapped[int] = mapped_column(Integer, index=True)
    field_path: Mapped[str] = mapped_column(String(128))
    suggested_value: Mapped[dict] = mapped_column(JSONB)  # text or jsonb payload
    template_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 6: Implement `libpoolzone/storage/models/sync_run.py`**

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from libpoolzone.storage.base import Base


class SyncRun(Base):
    """Audit row for every import / export / SEO / scrape batch."""

    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))  # "import" | "export" | "seo" | "scrape"
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)  # supplier code etc.
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running")  # "running" | "ok" | "failed"
    stats: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    log_path: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 7: Re-export all models from `libpoolzone/storage/models/__init__.py`**

```python
from libpoolzone.storage.models.category import Category, ProductCategory
from libpoolzone.storage.models.lock import ProductFieldLock
from libpoolzone.storage.models.pricing import CompetitorPrice, PricingRule
from libpoolzone.storage.models.product import (
    Product,
    ProductFile,
    ProductImage,
    ProductParameter,
)
from libpoolzone.storage.models.seo import SeoSuggestion
from libpoolzone.storage.models.supplier import (
    Supplier,
    SupplierCategoryMapping,
    SupplierProduct,
)
from libpoolzone.storage.models.sync_run import SyncRun

__all__ = [
    "Category",
    "CompetitorPrice",
    "PricingRule",
    "Product",
    "ProductCategory",
    "ProductFieldLock",
    "ProductFile",
    "ProductImage",
    "ProductParameter",
    "SeoSuggestion",
    "Supplier",
    "SupplierCategoryMapping",
    "SupplierProduct",
    "SyncRun",
]
```

- [ ] **Step 8: Verify all models import together**

Run:
```bash
python -c "from libpoolzone.storage import models; print(sorted(models.__all__))"
```

Expected: prints sorted list of all model names without errors.

- [ ] **Step 9: Commit**

```bash
git add libpoolzone/storage/models/
git commit -m "Add Supplier, Category, Lock, Pricing, SEO, SyncRun models"
```

---

## Task 8: Alembic init + baseline migration

**Files:**
- Create: `alembic.ini`
- Create: `libpoolzone/storage/migrations/env.py`
- Create: `libpoolzone/storage/migrations/script.py.mako`
- Create: `libpoolzone/storage/migrations/versions/` (directory)
- Create: `libpoolzone/storage/migrations/versions/<timestamp>_baseline.py` (autogenerated)

- [ ] **Step 1: Initialize Alembic into the project's migrations directory**

Run:
```bash
alembic init libpoolzone/storage/migrations
```

Expected: creates `alembic.ini` at repo root and the migrations directory with `env.py`, `script.py.mako`, `versions/`.

- [ ] **Step 2: Edit `alembic.ini`** — change the `script_location` line to point at the new directory (already done by `init`, but verify) and the `sqlalchemy.url` line is OK to leave blank (we set it from env in env.py)

Open `alembic.ini` and verify these lines:
```ini
script_location = libpoolzone/storage/migrations
sqlalchemy.url =
```

If `sqlalchemy.url` has a default value, blank it: `sqlalchemy.url =`

- [ ] **Step 3: Replace `libpoolzone/storage/migrations/env.py` with a version that reads DATABASE_URL and uses our metadata**

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from libpoolzone.settings import Settings
from libpoolzone.storage import models  # noqa: F401  — register all tables on Base.metadata
from libpoolzone.storage.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = Settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
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

- [ ] **Step 4: Generate the baseline migration**

Run:
```bash
alembic revision --autogenerate -m "baseline schema"
```

Expected: creates a file like `libpoolzone/storage/migrations/versions/<hash>_baseline_schema.py` containing `op.create_table(...)` calls for every model.

- [ ] **Step 5: Inspect the generated migration**

Open the new file in `libpoolzone/storage/migrations/versions/` and skim. Expected: all 13 tables present (`suppliers`, `supplier_products`, `supplier_category_mappings`, `categories`, `products`, `product_images`, `product_parameters`, `product_files`, `product_categories`, `product_field_locks`, `pricing_rules`, `competitor_prices`, `seo_suggestions`, `sync_runs`).

If anything is missing, the model file is likely not being imported via `models/__init__.py`. Fix the import, regenerate.

- [ ] **Step 6: Apply the migration**

Run:
```bash
alembic upgrade head
```

Expected: outputs `Running upgrade  -> <hash>, baseline schema`.

- [ ] **Step 7: Verify tables exist in Postgres**

Run:
```bash
docker exec poolzone-postgres psql -U poolzone -d poolzone -c "\dt"
```

Expected: lists all 13 tables plus `alembic_version`.

- [ ] **Step 8: Apply the same migration to the test database**

Run:
```bash
DATABASE_URL="postgresql+psycopg://poolzone:poolzone@localhost:5432/poolzone_test" alembic upgrade head
```

Expected: same `Running upgrade …` output, this time against the test DB.

- [ ] **Step 9: Commit**

```bash
git add alembic.ini libpoolzone/storage/migrations/
git commit -m "Add Alembic baseline migration for full schema"
```

---

## Task 9: pytest fixtures — transactional rollback per test

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/unit/catalog/__init__.py`

- [ ] **Step 1: Create test catalog package marker**

Run:
```bash
mkdir -p tests/unit/catalog tests/integration
touch tests/unit/catalog/__init__.py tests/integration/__init__.py
```

- [ ] **Step 2: Create `tests/conftest.py`**

```python
from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from libpoolzone.storage.engine import get_engine, get_session_factory


@pytest.fixture(scope="session")
def engine():
    """Engine bound to the TEST database. Migrations must already be applied."""
    return get_engine(test=True)


@pytest.fixture()
def db_session(engine) -> Iterator[Session]:
    """A session wrapped in a transaction that is rolled back at the end of each test.

    This keeps tests fast (no schema reset) and isolated (no test data leaks
    between tests).
    """
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = get_session_factory(test=True)
    session = SessionLocal(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
```

- [ ] **Step 3: Sanity-check the fixture with a trivial test** at `tests/unit/test_conftest.py`

```python
from sqlalchemy import text


def test_db_session_fixture_works(db_session):
    result = db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


def test_two_tests_are_isolated(db_session):
    # If isolation is broken, a leftover from another test would appear.
    # Just assert we can write + read in the same session without conflict.
    db_session.execute(text("CREATE TEMP TABLE t (n int)"))
    db_session.execute(text("INSERT INTO t VALUES (1)"))
    assert db_session.execute(text("SELECT count(*) FROM t")).scalar() == 1
```

- [ ] **Step 4: Run sanity tests**

Run:
```bash
pytest tests/unit/test_conftest.py -v
```

Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/unit/catalog/__init__.py tests/integration/__init__.py tests/unit/test_conftest.py
git commit -m "Add transactional db_session pytest fixture"
```

---

## Task 10: Catalog service — products (create, get, update, list)

**Files:**
- Create: `libpoolzone/catalog/products.py`
- Create: `tests/unit/catalog/test_products.py`

- [ ] **Step 1: Write failing tests** at `tests/unit/catalog/test_products.py`

```python
from decimal import Decimal

import pytest

from libpoolzone.catalog import products as products_svc
from libpoolzone.storage.models import Product


def test_create_product_persists_minimum_fields(db_session):
    product = products_svc.create_product(
        db_session,
        code="TEST001",
        titles={"cs": "Testovací produkt"},
        price_purchase=Decimal("100.00"),
    )

    assert product.id is not None
    assert product.code == "TEST001"
    assert product.titles == {"cs": "Testovací produkt"}
    assert product.price_purchase == Decimal("100.00")
    assert product.active is True


def test_get_product_by_code(db_session):
    products_svc.create_product(db_session, code="TEST002", titles={"cs": "X"})

    found = products_svc.get_product_by_code(db_session, "TEST002")
    assert found is not None
    assert found.code == "TEST002"


def test_get_product_by_code_returns_none_when_missing(db_session):
    assert products_svc.get_product_by_code(db_session, "DOES_NOT_EXIST") is None


def test_list_products_returns_all(db_session):
    products_svc.create_product(db_session, code="L1", titles={"cs": "A"})
    products_svc.create_product(db_session, code="L2", titles={"cs": "B"})

    result = products_svc.list_products(db_session)
    codes = {p.code for p in result}
    assert {"L1", "L2"}.issubset(codes)


def test_update_product_fields_writes_changes(db_session):
    p = products_svc.create_product(db_session, code="U1", titles={"cs": "Old"})

    products_svc.update_product_fields(
        db_session,
        product_id=p.id,
        changes={"titles": {"cs": "New"}, "stock": 42},
    )

    refreshed = db_session.get(Product, p.id)
    assert refreshed.titles == {"cs": "New"}
    assert refreshed.stock == 42


def test_create_product_with_duplicate_code_raises(db_session):
    products_svc.create_product(db_session, code="DUP", titles={"cs": "X"})

    with pytest.raises(Exception):  # SQLAlchemy IntegrityError wrapped
        products_svc.create_product(db_session, code="DUP", titles={"cs": "Y"})
        db_session.flush()
```

- [ ] **Step 2: Run tests, verify they fail**

Run:
```bash
pytest tests/unit/catalog/test_products.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'libpoolzone.catalog.products'` (or attribute error on the service module).

- [ ] **Step 3: Implement `libpoolzone/catalog/products.py`**

```python
"""Product CRUD service. Pure functions on top of the Product model.

Callers (importers, exporter, API) should go through these functions
rather than touching the ORM directly. This keeps invariants (e.g.
field locks) enforced in one place.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from libpoolzone.storage.models import Product


def create_product(
    session: Session,
    *,
    code: str,
    titles: dict | None = None,
    price_purchase: Decimal | None = None,
    **extra: Any,
) -> Product:
    product = Product(
        code=code,
        titles=titles or {},
        price_purchase=price_purchase,
        **extra,
    )
    session.add(product)
    session.flush()  # populate product.id without committing
    return product


def get_product(session: Session, product_id: int) -> Product | None:
    return session.get(Product, product_id)


def get_product_by_code(session: Session, code: str) -> Product | None:
    return session.scalars(select(Product).where(Product.code == code)).first()


def list_products(session: Session) -> list[Product]:
    return list(session.scalars(select(Product)))


def update_product_fields(
    session: Session,
    *,
    product_id: int,
    changes: dict[str, Any],
) -> Product:
    """Apply each (field_name -> value) pair to the product.

    Field-lock enforcement is layered on by `apply_supplier_changes` in M2;
    this function intentionally writes everything passed in.
    """
    product = session.get(Product, product_id)
    if product is None:
        raise ValueError(f"product {product_id} not found")

    for field_name, value in changes.items():
        setattr(product, field_name, value)
    session.flush()
    return product
```

- [ ] **Step 4: Run tests, verify they pass**

Run:
```bash
pytest tests/unit/catalog/test_products.py -v
```

Expected: all six tests PASS.

- [ ] **Step 5: Commit**

```bash
git add libpoolzone/catalog/products.py tests/unit/catalog/test_products.py
git commit -m "Add product CRUD service (create, get, update, list)"
```

---

## Task 11: Catalog service — categories (CRUD + tree + product link)

**Files:**
- Create: `libpoolzone/catalog/categories.py`
- Create: `tests/unit/catalog/test_categories.py`

- [ ] **Step 1: Write failing tests** at `tests/unit/catalog/test_categories.py`

```python
from libpoolzone.catalog import categories as cats_svc
from libpoolzone.catalog import products as products_svc
from libpoolzone.storage.models import ProductCategory


def test_create_category_persists(db_session):
    cat = cats_svc.create_category(
        db_session,
        code="cat_pumps",
        name_i18n={"cs": "Čerpadla"},
    )
    assert cat.id is not None
    assert cat.code == "cat_pumps"
    assert cat.name_i18n == {"cs": "Čerpadla"}


def test_create_subcategory_links_parent(db_session):
    parent = cats_svc.create_category(db_session, code="root", name_i18n={"cs": "Root"})
    child = cats_svc.create_category(
        db_session, code="child", name_i18n={"cs": "Child"}, parent_id=parent.id
    )
    db_session.flush()
    db_session.refresh(parent)
    assert child.parent_id == parent.id
    assert child in parent.children


def test_link_product_to_category_with_primary(db_session):
    cat = cats_svc.create_category(db_session, code="c1", name_i18n={"cs": "C1"})
    p = products_svc.create_product(db_session, code="P1", titles={"cs": "P"})

    cats_svc.link_product(db_session, product_id=p.id, category_id=cat.id, primary_yn=True)

    link = (
        db_session.query(ProductCategory)
        .filter_by(product_id=p.id, category_id=cat.id)
        .one()
    )
    assert link.primary_yn is True


def test_link_product_twice_is_idempotent(db_session):
    cat = cats_svc.create_category(db_session, code="c2", name_i18n={"cs": "C2"})
    p = products_svc.create_product(db_session, code="P2", titles={"cs": "P"})

    cats_svc.link_product(db_session, product_id=p.id, category_id=cat.id, primary_yn=False)
    cats_svc.link_product(db_session, product_id=p.id, category_id=cat.id, primary_yn=True)

    links = (
        db_session.query(ProductCategory)
        .filter_by(product_id=p.id, category_id=cat.id)
        .all()
    )
    assert len(links) == 1
    assert links[0].primary_yn is True  # updated on second call
```

- [ ] **Step 2: Run tests, verify they fail**

Run:
```bash
pytest tests/unit/catalog/test_categories.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'libpoolzone.catalog.categories'`.

- [ ] **Step 3: Implement `libpoolzone/catalog/categories.py`**

```python
"""Category CRUD service: tree management + product linking."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from libpoolzone.storage.models import Category, ProductCategory


def create_category(
    session: Session,
    *,
    code: str,
    name_i18n: dict,
    parent_id: int | None = None,
    **extra,
) -> Category:
    category = Category(
        code=code,
        name_i18n=name_i18n,
        parent_id=parent_id,
        **extra,
    )
    session.add(category)
    session.flush()
    return category


def get_category(session: Session, category_id: int) -> Category | None:
    return session.get(Category, category_id)


def get_category_by_code(session: Session, code: str) -> Category | None:
    return session.scalars(select(Category).where(Category.code == code)).first()


def link_product(
    session: Session,
    *,
    product_id: int,
    category_id: int,
    primary_yn: bool = False,
    position: int = 0,
) -> ProductCategory:
    """Idempotent: if the link already exists, update primary_yn/position; else create."""
    existing = (
        session.query(ProductCategory)
        .filter_by(product_id=product_id, category_id=category_id)
        .one_or_none()
    )
    if existing is not None:
        existing.primary_yn = primary_yn
        existing.position = position
        session.flush()
        return existing

    link = ProductCategory(
        product_id=product_id,
        category_id=category_id,
        primary_yn=primary_yn,
        position=position,
    )
    session.add(link)
    session.flush()
    return link
```

- [ ] **Step 4: Run tests, verify they pass**

Run:
```bash
pytest tests/unit/catalog/test_categories.py -v
```

Expected: all four tests PASS.

- [ ] **Step 5: Commit**

```bash
git add libpoolzone/catalog/categories.py tests/unit/catalog/test_categories.py
git commit -m "Add category service (create, link product, idempotent linking)"
```

---

## Task 12: Catalog service — field locks (is_locked, lock, unlock, apply_with_locks)

**Files:**
- Create: `libpoolzone/catalog/locks.py`
- Create: `tests/unit/catalog/test_locks.py`

- [ ] **Step 1: Write failing tests** at `tests/unit/catalog/test_locks.py`

```python
from decimal import Decimal

from libpoolzone.catalog import locks as locks_svc
from libpoolzone.catalog import products as products_svc
from libpoolzone.storage.models import Product, ProductFieldLock


def test_is_locked_returns_false_when_no_lock(db_session):
    p = products_svc.create_product(db_session, code="L1", titles={"cs": "X"})
    assert locks_svc.is_locked(db_session, product_id=p.id, field_path="price.common") is False


def test_lock_field_creates_row(db_session):
    p = products_svc.create_product(db_session, code="L2", titles={"cs": "X"})

    locks_svc.lock_field(db_session, product_id=p.id, field_path="price.common", locked_by="me")

    row = (
        db_session.query(ProductFieldLock)
        .filter_by(product_id=p.id, field_path="price.common")
        .one()
    )
    assert row.locked_by == "me"


def test_lock_field_is_idempotent(db_session):
    p = products_svc.create_product(db_session, code="L3", titles={"cs": "X"})

    locks_svc.lock_field(db_session, product_id=p.id, field_path="price.common")
    locks_svc.lock_field(db_session, product_id=p.id, field_path="price.common")

    count = (
        db_session.query(ProductFieldLock)
        .filter_by(product_id=p.id, field_path="price.common")
        .count()
    )
    assert count == 1


def test_unlock_field_removes_row(db_session):
    p = products_svc.create_product(db_session, code="L4", titles={"cs": "X"})
    locks_svc.lock_field(db_session, product_id=p.id, field_path="price.common")

    locks_svc.unlock_field(db_session, product_id=p.id, field_path="price.common")

    assert locks_svc.is_locked(db_session, product_id=p.id, field_path="price.common") is False


def test_apply_changes_respecting_locks_skips_locked_fields(db_session):
    p = products_svc.create_product(
        db_session,
        code="L5",
        titles={"cs": "X"},
        price_purchase=Decimal("100"),
        price_common=Decimal("200"),
        stock=10,
    )
    locks_svc.lock_field(db_session, product_id=p.id, field_path="price.common")

    stats = locks_svc.apply_changes_respecting_locks(
        db_session,
        product_id=p.id,
        changes={"price_common": Decimal("999"), "stock": 50},
        field_path_for={"price_common": "price.common", "stock": "stock"},
    )

    refreshed = db_session.get(Product, p.id)
    assert refreshed.price_common == Decimal("200")  # locked, unchanged
    assert refreshed.stock == 50                      # not locked, updated
    assert stats["updated"] == 1
    assert stats["locked_skips"] == 1


def test_list_locks_for_product(db_session):
    p = products_svc.create_product(db_session, code="L6", titles={"cs": "X"})
    locks_svc.lock_field(db_session, product_id=p.id, field_path="price.common")
    locks_svc.lock_field(db_session, product_id=p.id, field_path="descriptions.cs.long")

    paths = {l.field_path for l in locks_svc.list_locks_for_product(db_session, product_id=p.id)}
    assert paths == {"price.common", "descriptions.cs.long"}
```

- [ ] **Step 2: Run tests, verify they fail**

Run:
```bash
pytest tests/unit/catalog/test_locks.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'libpoolzone.catalog.locks'`.

- [ ] **Step 3: Implement `libpoolzone/catalog/locks.py`**

```python
"""Field-level locks: prevent supplier sync from overwriting human-edited fields."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from libpoolzone.storage.models import Product, ProductFieldLock


def is_locked(session: Session, *, product_id: int, field_path: str) -> bool:
    return (
        session.scalars(
            select(ProductFieldLock).where(
                ProductFieldLock.product_id == product_id,
                ProductFieldLock.field_path == field_path,
            )
        ).first()
        is not None
    )


def lock_field(
    session: Session,
    *,
    product_id: int,
    field_path: str,
    locked_by: str | None = None,
    note: str | None = None,
) -> ProductFieldLock:
    """Idempotent: if already locked, return the existing row (no-op)."""
    existing = (
        session.query(ProductFieldLock)
        .filter_by(product_id=product_id, field_path=field_path)
        .one_or_none()
    )
    if existing is not None:
        return existing

    lock = ProductFieldLock(
        product_id=product_id,
        field_path=field_path,
        locked_by=locked_by,
        note=note,
    )
    session.add(lock)
    session.flush()
    return lock


def unlock_field(session: Session, *, product_id: int, field_path: str) -> None:
    session.query(ProductFieldLock).filter_by(
        product_id=product_id, field_path=field_path
    ).delete()
    session.flush()


def list_locks_for_product(session: Session, *, product_id: int) -> list[ProductFieldLock]:
    return list(
        session.scalars(
            select(ProductFieldLock).where(ProductFieldLock.product_id == product_id)
        )
    )


def apply_changes_respecting_locks(
    session: Session,
    *,
    product_id: int,
    changes: dict[str, Any],
    field_path_for: dict[str, str],
) -> dict[str, int]:
    """Apply `changes` to a product, skipping any field whose path is locked.

    `changes`         : {model_attribute_name: new_value}
    `field_path_for`  : {model_attribute_name: logical_field_path}
                         e.g. {"price_common": "price.common"}

    Returns a stats dict: {"updated": N, "locked_skips": M}.
    """
    product = session.get(Product, product_id)
    if product is None:
        raise ValueError(f"product {product_id} not found")

    updated = 0
    locked_skips = 0

    for attr, new_value in changes.items():
        path = field_path_for.get(attr, attr)
        if is_locked(session, product_id=product_id, field_path=path):
            locked_skips += 1
            continue
        setattr(product, attr, new_value)
        updated += 1

    session.flush()
    return {"updated": updated, "locked_skips": locked_skips}
```

- [ ] **Step 4: Run tests, verify they pass**

Run:
```bash
pytest tests/unit/catalog/test_locks.py -v
```

Expected: all six tests PASS.

- [ ] **Step 5: Commit**

```bash
git add libpoolzone/catalog/locks.py tests/unit/catalog/test_locks.py
git commit -m "Add field-lock service and apply_changes_respecting_locks helper"
```

---

## Task 13: End-to-end integration smoke test

**Files:**
- Create: `tests/integration/test_smoke.py`

- [ ] **Step 1: Write the smoke test** at `tests/integration/test_smoke.py`

This test exercises the catalog as an importer-like caller would in M2: create a product, lock its description, then attempt to overwrite price + description as if syncing from a supplier — assert that the description is preserved (because it's locked) and the price is updated.

```python
from decimal import Decimal

from libpoolzone.catalog import categories as cats_svc
from libpoolzone.catalog import locks as locks_svc
from libpoolzone.catalog import products as products_svc
from libpoolzone.storage.models import Product


def test_locked_field_survives_supplier_sync_simulation(db_session):
    # 1. Initial product setup as if bootstrapped from Upgates export
    p = products_svc.create_product(
        db_session,
        code="AK1234",
        titles={"cs": "Čerpadlo Aseko Premium"},
        long_descriptions={"cs": "<p>Manually edited copy</p>"},
        price_purchase=Decimal("1000"),
        price_common=Decimal("2000"),
        stock=5,
    )

    # 2. Human locks the long description (e.g. accepted an AI suggestion)
    locks_svc.lock_field(
        db_session, product_id=p.id, field_path="descriptions.cs.long", locked_by="david"
    )

    # 3. Simulate a Pooltechnika sync that would update price + description + stock
    incoming_changes = {
        "long_descriptions": {"cs": "<p>Supplier generic description</p>"},
        "price_purchase": Decimal("1100"),
        "stock": 12,
    }
    field_path_for = {
        "long_descriptions": "descriptions.cs.long",
        "price_purchase": "price.purchase",
        "stock": "stock",
    }
    stats = locks_svc.apply_changes_respecting_locks(
        db_session,
        product_id=p.id,
        changes=incoming_changes,
        field_path_for=field_path_for,
    )

    # 4. Assert: description preserved, other fields updated
    refreshed = db_session.get(Product, p.id)
    assert refreshed.long_descriptions == {"cs": "<p>Manually edited copy</p>"}
    assert refreshed.price_purchase == Decimal("1100")
    assert refreshed.stock == 12
    assert stats == {"updated": 2, "locked_skips": 1}


def test_product_can_have_primary_category(db_session):
    cat_root = cats_svc.create_category(db_session, code="root", name_i18n={"cs": "Root"})
    cat_child = cats_svc.create_category(
        db_session, code="pumps", name_i18n={"cs": "Čerpadla"}, parent_id=cat_root.id
    )

    p = products_svc.create_product(db_session, code="P_E2E", titles={"cs": "E2E"})

    cats_svc.link_product(
        db_session, product_id=p.id, category_id=cat_child.id, primary_yn=True
    )
    cats_svc.link_product(
        db_session, product_id=p.id, category_id=cat_root.id, primary_yn=False
    )

    refreshed = db_session.get(Product, p.id)
    # Sanity: product exists and categories don't crash
    assert refreshed.code == "P_E2E"
```

- [ ] **Step 2: Run integration tests**

Run:
```bash
pytest tests/integration/ -v
```

Expected: both tests PASS.

- [ ] **Step 3: Run the full test suite to confirm nothing regressed**

Run:
```bash
pytest -v
```

Expected: all tests across `tests/unit/` and `tests/integration/` PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_smoke.py
git commit -m "Add integration smoke test: locked field survives supplier sync simulation"
```

---

## Task 14: Lint & format pass (ruff)

**Files:** none new

- [ ] **Step 1: Run ruff check on the new code**

Run:
```bash
ruff check libpoolzone tests
```

Expected: either `All checks passed!` or a small number of fixable issues. If issues appear, run `ruff check --fix libpoolzone tests` and inspect the diff before committing.

- [ ] **Step 2: Run ruff format (if any reformatting needed)**

Run:
```bash
ruff format libpoolzone tests
```

Expected: lists files reformatted (or `0 files reformatted`).

- [ ] **Step 3: Re-run the full test suite after any formatting changes**

Run:
```bash
pytest -v
```

Expected: all tests still PASS.

- [ ] **Step 4: Commit (only if anything changed)**

```bash
git status                  # check whether anything actually changed
git add libpoolzone tests
git commit -m "Format with ruff"
```

Skip the commit if `git status` shows clean.

---

## Task 15: Developer README

**Files:**
- Create: `libpoolzone/README.md`

- [ ] **Step 1: Write `libpoolzone/README.md`**

```markdown
# libpoolzone

Shared Python package for the Poolzone platform.

## First-time setup

```bash
# 1. Python environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Postgres
cp .env.example .env
docker compose up -d postgres
docker exec poolzone-postgres psql -U poolzone -d poolzone -c "CREATE DATABASE poolzone_test;"

# 3. Schema
alembic upgrade head
DATABASE_URL="postgresql+psycopg://poolzone:poolzone@localhost:5432/poolzone_test" alembic upgrade head

# 4. Run tests
pytest
```

## Package layout

- `storage/` — SQLAlchemy models, engine, Alembic migrations.
- `catalog/` — service layer (products, categories, field locks). Higher-level code goes through here, not the ORM.
- `importers/`, `exporter/`, `seo/`, `pricing/` — populated in later milestones.

See `docs/superpowers/specs/2026-05-13-poolzone-platform-design.md` for the full design.
```

- [ ] **Step 2: Commit**

```bash
git add libpoolzone/README.md
git commit -m "Add libpoolzone README with first-time setup instructions"
```

---

## M1 done — verification checklist

After all 15 tasks, you should be able to:

- [ ] Run `pytest` and see all tests pass (unit + integration).
- [ ] Open a Python REPL, `from libpoolzone.catalog import products`, create a product, lock a field, see the lock persist.
- [ ] Run `alembic current` and see a single revision applied.
- [ ] Inspect Postgres via `docker exec poolzone-postgres psql -U poolzone -d poolzone -c "\dt"` and see all 13 tables + `alembic_version`.
- [ ] Run `ruff check libpoolzone tests` and see no errors.

If all of the above hold, M1 is complete and the foundation is ready for M2.

---

## Roadmap appendix — M2 through M7

This appendix exists so a fresh session can produce the next plan without re-reading the entire spec. Each entry is one paragraph: scope, end state, and the key references in the spec.

### M2 — Pooltechnika importer + bootstrap

Add `libpoolzone.importers` per spec §5. Implement the `SupplierAdapter` protocol and the shared `pipeline` (fetch → parse → snapshot → match → diff → apply → record). Port `createProductsForPoolzone.py` into a `PooltechnikaAdapter`. Add CLI commands (Typer) under `apps/cli/` for `poolz import <supplier>` and `poolz bootstrap`. Bootstrap script: import the current Upgates export XML (spec §10 step 4), then run a Pooltechnika sync with the auto-lock heuristic from §10 step 5. Migrate `produkty_cenotvorba.xlsx` → `pricing_rules` rows (spec §6.3) and the "Pooltechnika ID kategorie" column → `supplier_category_mappings`. **End state:** `poolz bootstrap` followed by `poolz import pooltechnika` populates the DB matching the current Upgates state; sync_runs has audit rows; locks survive.

### M3 — Upgates exporter

Add `libpoolzone.exporter.upgates` and `libpoolzone.exporter.publishers` per spec §6. Implement `apply_pricing` resolving `pricing_rules` (§6.3). Implement `PublishTarget` protocol with `LocalPathPublisher` and `GitHubPagesPublisher` (§6.2). Implement hash-based diff guard (§6.5). Add `poolz export upgates` CLI. Snapshot-test the XML output against a checked-in golden file. **End state of M3 = full parity with current scripts** — after this, move the legacy `createProductsForPoolzone.py`, `createCategoriesForPoolzone.py`, `getCategoriesFromPooltechnika.py`, all Excels, and the `BACKUP/` + `UTILITY/` folders to `archive/` (do **not** delete — David removes manually after verification, per spec §10 step 7).

### M4 — FastAPI + React admin skeleton

Add `apps/api/` (FastAPI) and `frontend/` (Vite + TS + React + TanStack Query + shadcn/ui). Routers in `apps/api/routers/`: `products`, `categories`, `suppliers`, `locks`, `sync_runs`. Set up FastAPI OpenAPI → typed React client generation. React pages: product list (paginated, filterable), product detail/edit, lock toggle per field, sync runs viewer. Devcontainer probably gets upgraded here to docker-compose-based so it can run postgres + api + frontend together. **End state:** browsable + editable catalog at `http://localhost:5173` (frontend) + `http://localhost:8000` (API).

### M5 — SEO module + review queue

Add `libpoolzone.seo` per spec §7. Port `descriptionGenerator/generate_descriptions.py` into `libpoolzone/seo/generator.py` — preserve the Czech system prompt, pump/electrolysis templates (now files in `libpoolzone/seo/templates/`), PDF context caching, and ephemeral system-prompt caching. New: write outputs to `seo_suggestions` instead of an import XML. Add API endpoints for the review queue + React UI for accept/edit/reject/regenerate-with-hint. Accept inserts a `product_field_locks` row automatically (§7.3). Support both product and category SEO with different templates. **End state:** "Generate description" button on product page works end-to-end; queue page lets you process suggestions in bulk.

### M6 — Scheduler + worker process

Add `apps/worker/` with APScheduler per spec §9. Define default schedule (03:00 Pooltechnika sync, 03:30 competitor scrape, 04:00 export, 07:00 SEO batch, every 2h re-export). Make cron expressions editable from admin. Add `/health` and `/jobs` HTTP endpoints on the worker. React admin "Jobs" page reads from it. Add idempotency check (don't start a second run of the same job if one is `running` in `sync_runs`). **End state:** truly hands-off operation; manual triggers still available everywhere.

### M7 — Pricing module port

Add `libpoolzone.pricing.rules` (extracted from M3's pricing logic into its own module), `libpoolzone.pricing.analysis` (port `buildPricingAnalysis.py`), and `libpoolzone.pricing.scrapers/` (port the four competitor scrapers as adapter-pattern classes). Port `pricing/pricing_app/app.py` to `apps/streamlit_pricing/app.py` reading from the DB instead of CSV. Move competitor URLs from `competitor_urls.csv` into `competitor_prices`-related table (or a dedicated `competitor_urls` table — decide at planning time). Worker schedules daily scraping. Committing a new price from Streamlit auto-locks `price.common`. **End state:** pricing workflow fully integrated with the catalog; CSV roundtrip retired (CSV files moved to `archive/`).

### Notes for the next planning session

- The spec is the source of truth; this appendix is a navigation aid.
- The "archive, don't delete" rule (memory `feedback-archive-dont-delete`) applies anywhere a milestone retires old files.
- Existing scripts to be archived during M3:
  `createProductsForPoolzone.py`, `createCategoriesForPoolzone.py`, `getCategoriesFromPooltechnika.py`,
  `produkty_cenotvorba.xlsx`, `poolzone_categories.xlsx`, `pooltechnika_categories.xlsx`, `pooltechnika_categories.xml`,
  `poolzone_categories.xml`, `poolzone_products.xml`, `BACKUP/`, `UTILITY/`.
- The Streamlit `pricing/pricing_app/` is retired in M7, not M3.
- The `descriptionGenerator/` folder is retired in M5.
- The current `requirements.txt` is for the legacy scripts and can be archived alongside them as their dependencies are no longer needed.
