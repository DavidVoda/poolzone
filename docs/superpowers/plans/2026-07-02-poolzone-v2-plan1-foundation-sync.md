# Poolzone v2 — Plan 1: Foundation + Pooltechnika Sync

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the `poolzoneV2/` Python project (Postgres schema + migrations) and a working Pooltechnika supplier sync that pulls the Heureka feed into the database honoring create-full / update-whitelist, with integration tests against a fixture.

**Architecture:** Single Python package `app` inside `poolzoneV2/`. SQLAlchemy 2.0 models + Alembic migrations against Postgres (docker-compose). Sync = a per-supplier adapter (`fetch` + `parse` → `ParsedProduct`) feeding a shared pipeline whose upsert step enforces create-full for new products and update-whitelist for existing ones, recording every run to `job_runs`.

**Tech Stack:** Python 3.12, SQLAlchemy 2.0, Alembic, Postgres 16, pytest, requests, Typer (CLI). Ruff for formatting.

**Scope note:** This is the first of four V1 plans. Later plans (separate files): Plan 2 = Pricing + Upgates XML export; Plan 3 = FastAPI + React GUI; Plan 4 = Bootstrap & cut-over. This plan stops at "feed lands in DB correctly, verified by tests." No pricing math, no XML, no HTTP API here.

**Spec:** `docs/superpowers/specs/2026-07-02-poolzone-middleware-v2-design.md` (§3 architecture, §4 data model, §5 sync).

---

## File Structure

```
poolzoneV2/
├── pyproject.toml              # project + deps + pytest/ruff config
├── docker-compose.yml          # postgres for dev + test
├── .env.example                # DATABASE_URL etc.
├── alembic.ini
├── app/
│   ├── __init__.py
│   ├── settings.py             # env config
│   ├── db.py                   # engine, SessionLocal, Base, session_scope
│   ├── models.py               # all SQLAlchemy models
│   ├── migrations/             # alembic env + versions
│   │   ├── env.py
│   │   └── versions/
│   ├── sync/
│   │   ├── __init__.py
│   │   ├── types.py            # ParsedProduct, ParsedParam dataclasses
│   │   ├── pipeline.py         # run_sync(): create-full / update-whitelist + job_runs
│   │   └── suppliers/
│   │       ├── __init__.py
│   │       └── pooltechnika.py # fetch() + parse()
│   └── cli.py                  # `poolz sync <supplier_code>`
└── tests/
    ├── __init__.py
    ├── conftest.py             # transactional db_session fixture
    ├── fixtures/
    │   └── pooltechnika_sample.xml
    ├── test_pooltechnika_parse.py
    └── test_sync_pipeline.py
```

Each file has one responsibility. `models.py` stays single-file until it exceeds ~300 lines (it won't in V1). Adapters live under `sync/suppliers/` so adding a supplier is one new file.

---

### Task 1: Project skeleton

**Files:**
- Create: `poolzoneV2/pyproject.toml`
- Create: `poolzoneV2/app/__init__.py`
- Create: `poolzoneV2/tests/__init__.py`

- [ ] **Step 1: Create the package directories and empty init files**

```bash
mkdir -p poolzoneV2/app/sync/suppliers poolzoneV2/app/migrations/versions poolzoneV2/tests/fixtures
touch poolzoneV2/app/__init__.py poolzoneV2/app/sync/__init__.py poolzoneV2/app/sync/suppliers/__init__.py poolzoneV2/tests/__init__.py
```

- [ ] **Step 2: Write `poolzoneV2/pyproject.toml`**

```toml
[project]
name = "poolzone"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "psycopg[binary]>=3.1",
    "requests>=2.31",
    "typer>=0.12",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.6"]

[project.scripts]
poolz = "app.cli:app"

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]
```

- [ ] **Step 3: Create and populate the virtualenv**

Run:
```bash
cd poolzoneV2 && python3.12 -m venv .venv && ./.venv/bin/pip install -e ".[dev]"
```
Expected: installs without error, ends with `Successfully installed ... poolzone-0.1.0`.

- [ ] **Step 4: Commit**

```bash
cd /Users/dubelin/Documents/Poolzone/Git/poolzone
echo "poolzoneV2/.venv/" >> .gitignore
git add poolzoneV2/pyproject.toml poolzoneV2/app/__init__.py poolzoneV2/app/sync/__init__.py poolzoneV2/app/sync/suppliers/__init__.py poolzoneV2/tests/__init__.py .gitignore
git commit -m "feat(v2): project skeleton for poolzoneV2"
```

---

### Task 2: Postgres via docker-compose + settings

**Files:**
- Create: `poolzoneV2/docker-compose.yml`
- Create: `poolzoneV2/.env.example`
- Create: `poolzoneV2/app/settings.py`

- [ ] **Step 1: Write `poolzoneV2/docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: poolzone
      POSTGRES_PASSWORD: poolzone
      POSTGRES_DB: poolzone
    ports:
      - "5433:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

Port 5433 on host avoids clashing with any local Postgres on 5432.

- [ ] **Step 2: Write `poolzoneV2/.env.example`**

```
DATABASE_URL=postgresql+psycopg://poolzone:poolzone@localhost:5433/poolzone
```

- [ ] **Step 3: Write `poolzoneV2/app/settings.py`**

```python
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    database_url: str = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://poolzone:poolzone@localhost:5433/poolzone",
    )


settings = Settings()
```

- [ ] **Step 4: Start Postgres and verify it accepts connections**

Run:
```bash
cd poolzoneV2 && docker compose up -d && sleep 3 && docker compose exec -T db pg_isready -U poolzone
```
Expected: `/var/run/postgresql:5432 - accepting connections`

- [ ] **Step 5: Commit**

```bash
git add poolzoneV2/docker-compose.yml poolzoneV2/.env.example poolzoneV2/app/settings.py
git commit -m "feat(v2): postgres compose + settings"
```

---

### Task 3: Database core (Base, engine, session)

**Files:**
- Create: `poolzoneV2/app/db.py`

- [ ] **Step 1: Write `poolzoneV2/app/db.py`**

```python
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.settings import settings

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


@contextmanager
def session_scope():
    """Transactional session: commit on success, rollback on error, always close."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

- [ ] **Step 2: Verify it imports**

Run:
```bash
cd poolzoneV2 && ./.venv/bin/python -c "from app.db import Base, engine, session_scope; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add poolzoneV2/app/db.py
git commit -m "feat(v2): db base, engine, session_scope"
```

---

### Task 4: SQLAlchemy models

**Files:**
- Create: `poolzoneV2/app/models.py`

- [ ] **Step 1: Write `poolzoneV2/app/models.py`**

```python
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    feed_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Columns the sync is allowed to overwrite on an EXISTING product.
    update_whitelist: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=lambda: ["stock", "price_purchase", "availability"]
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("supplier_id", "code", name="uq_product_supplier_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(128), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    ean: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)

    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    long_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    seo_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    seo_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_slug: Mapped[str | None] = mapped_column(Text, nullable=True)

    stock: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[int | None] = mapped_column(Integer, nullable=True)  # grams
    availability: Mapped[str | None] = mapped_column(String(128), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    price_purchase: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    coefficient: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("1.0"))
    margin_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    params: Mapped[list[ProductParam]] = relationship(
        cascade="all, delete-orphan", back_populates="product"
    )
    images: Mapped[list[ProductImage]] = relationship(
        cascade="all, delete-orphan", back_populates="product"
    )


class ProductParam(Base):
    __tablename__ = "product_params"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    ord: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship(back_populates="params")


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(Text)
    alt: Mapped[str | None] = mapped_column(Text, nullable=True)
    ord: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship(back_populates="images")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    seo_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    seo_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    upgates_code: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ProductCategory(Base):
    __tablename__ = "product_categories"
    __table_args__ = (
        UniqueConstraint("product_id", "category_id", name="uq_product_category"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
    primary_yn: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)


class SupplierCategoryMap(Base):
    __tablename__ = "supplier_category_map"
    __table_args__ = (
        UniqueConstraint("supplier_id", "supplier_path", name="uq_supplier_path"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"))
    supplier_path: Mapped[str] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))


class PricingRule(Base):
    __tablename__ = "pricing_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(32))  # "default" | "manufacturer"
    match_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    margin_pct: Mapped[Decimal] = mapped_column(Numeric(5, 4))


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)  # "sync" | "export" | ...
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")  # running|success|failed|skipped
    stats: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 2: Verify models import and register on Base metadata**

Run:
```bash
cd poolzoneV2 && ./.venv/bin/python -c "from app import models; from app.db import Base; print(sorted(Base.metadata.tables))"
```
Expected: a list containing `categories`, `job_runs`, `pricing_rules`, `product_categories`, `product_images`, `product_params`, `products`, `supplier_category_map`, `suppliers`.

- [ ] **Step 3: Commit**

```bash
git add poolzoneV2/app/models.py
git commit -m "feat(v2): SQLAlchemy models"
```

---

### Task 5: Alembic baseline migration

**Files:**
- Create: `poolzoneV2/alembic.ini`
- Create: `poolzoneV2/app/migrations/env.py`
- Create: `poolzoneV2/app/migrations/script.py.mako`
- Create (generated): `poolzoneV2/app/migrations/versions/<hash>_baseline.py`

- [ ] **Step 1: Write `poolzoneV2/alembic.ini`**

```ini
[alembic]
script_location = app/migrations
prepend_sys_path = .

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

- [ ] **Step 2: Write `poolzoneV2/app/migrations/script.py.mako`**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    ${upgrades if upgrades else "pass"}


def downgrade():
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 3: Write `poolzoneV2/app/migrations/env.py`**

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import models  # noqa: F401  ensures models register on Base.metadata
from app.db import Base
from app.settings import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
```

- [ ] **Step 4: Autogenerate the baseline migration**

Run:
```bash
cd poolzoneV2 && ./.venv/bin/alembic revision --autogenerate -m "baseline"
```
Expected: creates `app/migrations/versions/<hash>_baseline.py`, output mentions `Detected added table 'suppliers'` (and the others).

- [ ] **Step 5: Apply the migration and verify tables exist**

Run:
```bash
cd poolzoneV2 && ./.venv/bin/alembic upgrade head && docker compose exec -T db psql -U poolzone -c "\dt"
```
Expected: table list includes `products`, `suppliers`, `job_runs`, etc., plus `alembic_version`.

- [ ] **Step 6: Commit**

```bash
git add poolzoneV2/alembic.ini poolzoneV2/app/migrations/
git commit -m "feat(v2): alembic baseline migration"
```

---

### Task 6: Transactional test fixture

**Files:**
- Create: `poolzoneV2/tests/conftest.py`

- [ ] **Step 1: Write `poolzoneV2/tests/conftest.py`**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.settings import settings


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(settings.database_url, future=True)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    """Each test runs in a transaction that is rolled back afterwards."""
    connection = engine.connect()
    trans = connection.begin()
    session = sessionmaker(bind=connection, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()
```

- [ ] **Step 2: Verify the fixture collects (no tests yet is fine)**

Run:
```bash
cd poolzoneV2 && ./.venv/bin/pytest -q
```
Expected: `no tests ran` (exit code 5) — confirms conftest imports cleanly with no collection errors.

- [ ] **Step 3: Commit**

```bash
git add poolzoneV2/tests/conftest.py
git commit -m "test(v2): transactional db_session fixture"
```

---

### Task 7: ParsedProduct types + Pooltechnika parse()

The Pooltechnika feed is Heureka XML: a root with `<SHOPITEM>` children. Relevant elements per item: `ITEM_ID`, `PRODUCTNAME`, `URL`, `IMGURL`, `PRICE_VAT` (purchase price **incl** 21% VAT), `EAN`, `MANUFACTURER`, `CATEGORYTEXT`, `stock_quantity`, and zero or more `<PARAM><PARAM_NAME>..</PARAM_NAME><VAL>..</VAL></PARAM>`. `parse()` returns `price_purchase` **excl** VAT (spec §5.2: adapters return purchase price excl VAT).

**Files:**
- Create: `poolzoneV2/app/sync/types.py`
- Create: `poolzoneV2/tests/fixtures/pooltechnika_sample.xml`
- Create: `poolzoneV2/app/sync/suppliers/pooltechnika.py`
- Create: `poolzoneV2/tests/test_pooltechnika_parse.py`

- [ ] **Step 1: Write `poolzoneV2/app/sync/types.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class ParsedParam:
    name: str
    value: str


@dataclass
class ParsedProduct:
    code: str
    title: str | None = None
    url: str | None = None
    ean: str | None = None
    manufacturer: str | None = None
    price_purchase: Decimal | None = None  # excl VAT
    stock: int | None = None
    weight: int | None = None  # grams
    availability: str | None = None
    category_path: str | None = None  # raw CATEGORYTEXT
    image_urls: list[str] = field(default_factory=list)
    params: list[ParsedParam] = field(default_factory=list)
```

- [ ] **Step 2: Write the test fixture `poolzoneV2/tests/fixtures/pooltechnika_sample.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<SHOP>
  <SHOPITEM>
    <ITEM_ID>AK13327</ITEM_ID>
    <PRODUCTNAME>OXY Pure Ag 5L</PRODUCTNAME>
    <URL>https://www.pooltechnika.cz/oxy-pure-ag-5l</URL>
    <IMGURL>https://img.pooltechnika.cz/oxy5l.jpg</IMGURL>
    <PRICE_VAT>1210,00</PRICE_VAT>
    <EAN>8594000000017</EAN>
    <MANUFACTURER>Aseko</MANUFACTURER>
    <CATEGORYTEXT>Chemie | Kyslíková</CATEGORYTEXT>
    <stock_quantity>7</stock_quantity>
    <PARAM>
      <PARAM_NAME>Hmotnost</PARAM_NAME>
      <VAL>5200 g</VAL>
    </PARAM>
    <PARAM>
      <PARAM_NAME>Objem</PARAM_NAME>
      <VAL>5 l</VAL>
    </PARAM>
  </SHOPITEM>
  <SHOPITEM>
    <ITEM_ID>20031-14</ITEM_ID>
    <PRODUCTNAME>pH minus 35 kg</PRODUCTNAME>
    <PRICE_VAT>605,00</PRICE_VAT>
    <CATEGORYTEXT>Chemie | pH</CATEGORYTEXT>
    <stock_quantity>0</stock_quantity>
  </SHOPITEM>
</SHOP>
```

- [ ] **Step 3: Write the failing test `poolzoneV2/tests/test_pooltechnika_parse.py`**

```python
from decimal import Decimal
from pathlib import Path

from app.sync.suppliers.pooltechnika import parse

FIXTURE = (Path(__file__).parent / "fixtures" / "pooltechnika_sample.xml").read_bytes()


def test_parse_returns_all_items():
    products = parse(FIXTURE)
    assert len(products) == 2


def test_parse_maps_first_item_fields():
    first = parse(FIXTURE)[0]
    assert first.code == "AK13327"
    assert first.title == "OXY Pure Ag 5L"
    assert first.url == "https://www.pooltechnika.cz/oxy-pure-ag-5l"
    assert first.ean == "8594000000017"
    assert first.manufacturer == "Aseko"
    assert first.stock == 7
    assert first.category_path == "Chemie | Kyslíková"
    assert first.image_urls == ["https://img.pooltechnika.cz/oxy5l.jpg"]


def test_parse_computes_purchase_price_excl_vat():
    # 1210,00 incl 21% VAT -> 1000.00 excl VAT
    first = parse(FIXTURE)[0]
    assert first.price_purchase == Decimal("1000.00")


def test_parse_extracts_weight_grams_from_param():
    first = parse(FIXTURE)[0]
    assert first.weight == 5200


def test_parse_keeps_all_params():
    first = parse(FIXTURE)[0]
    names = {p.name for p in first.params}
    assert names == {"Hmotnost", "Objem"}


def test_parse_handles_missing_optional_fields():
    second = parse(FIXTURE)[1]
    assert second.code == "20031-14"
    assert second.url is None
    assert second.manufacturer is None
    assert second.image_urls == []
    assert second.weight is None
    assert second.stock == 0
```

- [ ] **Step 4: Run the test to verify it fails**

Run:
```bash
cd poolzoneV2 && ./.venv/bin/pytest tests/test_pooltechnika_parse.py -q
```
Expected: FAIL — `ModuleNotFoundError` / `cannot import name 'parse'`.

- [ ] **Step 5: Write `poolzoneV2/app/sync/suppliers/pooltechnika.py`**

```python
from __future__ import annotations

import xml.etree.ElementTree as ET
from decimal import ROUND_HALF_UP, Decimal

import requests

from app.sync.types import ParsedParam, ParsedProduct

CODE = "pooltechnika"
VAT_RATE = Decimal("0.21")


def fetch(feed_url: str) -> bytes:
    """Download the Heureka feed. Network boundary — kept trivial and mockable."""
    resp = requests.get(feed_url, timeout=60)
    resp.raise_for_status()
    return resp.content


def _text(item: ET.Element, tag: str) -> str | None:
    el = item.find(tag)
    if el is None or el.text is None:
        return None
    val = el.text.strip()
    return val or None


def _purchase_excl_vat(price_vat_text: str | None) -> Decimal | None:
    if not price_vat_text:
        return None
    incl = Decimal(price_vat_text.replace(",", ".").strip())
    excl = incl / (Decimal("1") + VAT_RATE)
    return excl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _weight_grams(item: ET.Element) -> int | None:
    for param in item.findall("PARAM"):
        name = param.find("PARAM_NAME")
        val = param.find("VAL")
        if name is not None and name.text and name.text.strip() == "Hmotnost" and val is not None:
            digits = "".join(c for c in (val.text or "") if c.isdigit())
            return int(digits) if digits else None
    return None


def _params(item: ET.Element) -> list[ParsedParam]:
    out: list[ParsedParam] = []
    for param in item.findall("PARAM"):
        name = param.find("PARAM_NAME")
        val = param.find("VAL")
        if name is not None and name.text:
            out.append(ParsedParam(name=name.text.strip(), value=(val.text or "").strip() if val is not None else ""))
    return out


def parse(raw: bytes) -> list[ParsedProduct]:
    root = ET.fromstring(raw)
    products: list[ParsedProduct] = []
    for item in root.findall("SHOPITEM"):
        code = _text(item, "ITEM_ID")
        if not code:
            continue
        stock_text = _text(item, "stock_quantity")
        img = _text(item, "IMGURL")
        products.append(
            ParsedProduct(
                code=code,
                title=_text(item, "PRODUCTNAME"),
                url=_text(item, "URL"),
                ean=_text(item, "EAN"),
                manufacturer=_text(item, "MANUFACTURER"),
                price_purchase=_purchase_excl_vat(_text(item, "PRICE_VAT")),
                stock=int(stock_text) if stock_text is not None else None,
                weight=_weight_grams(item),
                availability=_text(item, "DELIVERY_DATE"),
                category_path=_text(item, "CATEGORYTEXT"),
                image_urls=[img] if img else [],
                params=_params(item),
            )
        )
    return products
```

- [ ] **Step 6: Run the test to verify it passes**

Run:
```bash
cd poolzoneV2 && ./.venv/bin/pytest tests/test_pooltechnika_parse.py -q
```
Expected: `6 passed`.

- [ ] **Step 7: Commit**

```bash
git add poolzoneV2/app/sync/types.py poolzoneV2/app/sync/suppliers/pooltechnika.py poolzoneV2/tests/test_pooltechnika_parse.py poolzoneV2/tests/fixtures/pooltechnika_sample.xml
git commit -m "feat(v2): pooltechnika parse() + ParsedProduct types"
```

---

### Task 8: Sync pipeline — create-full / update-whitelist

The pipeline is the only writer of supplier-sourced changes. New product (no `(supplier_id, code)` match) → create with **all** parsed fields including params and images. Existing product → update **only** the columns in `supplier.update_whitelist`. Categories are resolved via `supplier_category_map`; unmapped paths are counted, not fatal. Every run writes a `job_runs` row; an in-progress run of the same kind makes a new run record `skipped`.

**Files:**
- Create: `poolzoneV2/app/sync/pipeline.py`
- Create: `poolzoneV2/tests/test_sync_pipeline.py`

- [ ] **Step 1: Write the failing test `poolzoneV2/tests/test_sync_pipeline.py`**

```python
from decimal import Decimal

from app.models import JobRun, Product, ProductImage, ProductParam, Supplier
from app.sync.pipeline import run_sync
from app.sync.types import ParsedParam, ParsedProduct


def _supplier(db_session):
    s = Supplier(code="pooltechnika", name="Pooltechnika", feed_url="http://x")
    db_session.add(s)
    db_session.flush()
    return s


def _parsed(code, **kw):
    base = dict(
        title="T",
        price_purchase=Decimal("100.00"),
        stock=5,
        availability="skladem",
        image_urls=["http://img/1.jpg"],
        params=[ParsedParam("Hmotnost", "5200 g")],
    )
    base.update(kw)
    return ParsedProduct(code=code, **base)


def test_new_product_is_created_full(db_session):
    supplier = _supplier(db_session)
    stats = run_sync(db_session, supplier, [_parsed("AK1")])

    prod = db_session.query(Product).filter_by(supplier_id=supplier.id, code="AK1").one()
    assert prod.title == "T"
    assert prod.price_purchase == Decimal("100.00")
    assert prod.stock == 5
    assert db_session.query(ProductImage).filter_by(product_id=prod.id).count() == 1
    assert db_session.query(ProductParam).filter_by(product_id=prod.id).count() == 1
    assert stats["created"] == 1
    assert stats["updated"] == 0


def test_existing_product_updates_only_whitelist(db_session):
    supplier = _supplier(db_session)
    run_sync(db_session, supplier, [_parsed("AK1")])

    # Owner edits the title after creation.
    prod = db_session.query(Product).filter_by(code="AK1").one()
    prod.title = "OWNER EDIT"
    db_session.flush()

    # Supplier sends new title + new stock + new price.
    run_sync(
        db_session,
        supplier,
        [_parsed("AK1", title="SUPPLIER NEW TITLE", stock=99, price_purchase=Decimal("222.00"))],
    )

    prod = db_session.query(Product).filter_by(code="AK1").one()
    assert prod.title == "OWNER EDIT"          # NOT overwritten (not in whitelist)
    assert prod.stock == 99                    # whitelisted -> updated
    assert prod.price_purchase == Decimal("222.00")  # whitelisted -> updated


def test_existing_product_images_and_params_not_resynced(db_session):
    supplier = _supplier(db_session)
    run_sync(db_session, supplier, [_parsed("AK1")])
    run_sync(db_session, supplier, [_parsed("AK1", image_urls=["http://img/2.jpg", "http://img/3.jpg"])])

    prod = db_session.query(Product).filter_by(code="AK1").one()
    urls = {i.url for i in db_session.query(ProductImage).filter_by(product_id=prod.id)}
    assert urls == {"http://img/1.jpg"}  # original image kept, not replaced


def test_run_records_job_run(db_session):
    supplier = _supplier(db_session)
    run_sync(db_session, supplier, [_parsed("AK1"), _parsed("AK2")])
    job = db_session.query(JobRun).filter_by(kind="sync").order_by(JobRun.id.desc()).first()
    assert job.status == "success"
    assert job.stats["products_seen"] == 2
    assert job.stats["created"] == 2
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
cd poolzoneV2 && ./.venv/bin/pytest tests/test_sync_pipeline.py -q
```
Expected: FAIL — `cannot import name 'run_sync'`.

- [ ] **Step 3: Write `poolzoneV2/app/sync/pipeline.py`**

```python
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import JobRun, Product, ProductImage, ProductParam, Supplier
from app.sync.types import ParsedProduct

# Fields copied verbatim onto a NEW product (create-full). Whitelist controls updates.
_CREATE_FIELDS = (
    "title",
    "ean",
    "manufacturer",
    "price_purchase",
    "stock",
    "weight",
    "availability",
)


def _apply_create(product: Product, parsed: ParsedProduct) -> None:
    for f in _CREATE_FIELDS:
        setattr(product, f, getattr(parsed, f))
    product.images = [ProductImage(url=u, ord=i) for i, u in enumerate(parsed.image_urls)]
    product.params = [
        ProductParam(name=p.name, value=p.value, ord=i) for i, p in enumerate(parsed.params)
    ]


def _apply_update(product: Product, parsed: ParsedProduct, whitelist: list[str]) -> None:
    for field_name in whitelist:
        if hasattr(parsed, field_name):
            setattr(product, field_name, getattr(parsed, field_name))


def run_sync(session: Session, supplier: Supplier, parsed_products: list[ParsedProduct]) -> dict:
    """Create-full for new products, update-whitelist for existing. Records a JobRun."""
    # Overlap guard: refuse to run if another sync is already in progress.
    in_progress = session.execute(
        select(JobRun).where(JobRun.kind == "sync", JobRun.status == "running")
    ).first()
    if in_progress:
        job = JobRun(kind="sync", status="skipped", stats={"reason": "another sync running"})
        session.add(job)
        session.flush()
        return {"skipped": True}

    job = JobRun(kind="sync", status="running", stats={})
    session.add(job)
    session.flush()

    stats = {"products_seen": 0, "created": 0, "updated": 0, "errors": []}
    whitelist = supplier.update_whitelist or ["stock", "price_purchase", "availability"]

    for parsed in parsed_products:
        stats["products_seen"] += 1
        try:
            existing = session.execute(
                select(Product).where(
                    Product.supplier_id == supplier.id, Product.code == parsed.code
                )
            ).scalar_one_or_none()
            if existing is None:
                product = Product(code=parsed.code, supplier_id=supplier.id)
                _apply_create(product, parsed)
                session.add(product)
                stats["created"] += 1
            else:
                _apply_update(existing, parsed, whitelist)
                stats["updated"] += 1
        except Exception as exc:  # per-product isolation: one bad row never aborts the run
            stats["errors"].append({"code": parsed.code, "error": str(exc)})

    session.flush()
    supplier.last_synced_at = datetime.now(timezone.utc)
    job.status = "success"
    job.finished_at = datetime.now(timezone.utc)
    job.stats = stats
    session.flush()
    return stats
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
cd poolzoneV2 && ./.venv/bin/pytest tests/test_sync_pipeline.py -q
```
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add poolzoneV2/app/sync/pipeline.py poolzoneV2/tests/test_sync_pipeline.py
git commit -m "feat(v2): sync pipeline create-full / update-whitelist"
```

---

### Task 9: CLI entry point `poolz sync`

**Files:**
- Create: `poolzoneV2/app/cli.py`

- [ ] **Step 1: Write `poolzoneV2/app/cli.py`**

```python
from __future__ import annotations

import typer

from app.db import session_scope
from app.models import Supplier
from app.sync.pipeline import run_sync
from app.sync.suppliers import pooltechnika

app = typer.Typer(help="Poolzone middleware CLI")

# Registry: supplier code -> adapter module exposing fetch() + parse().
ADAPTERS = {pooltechnika.CODE: pooltechnika}


@app.command()
def sync(supplier_code: str) -> None:
    """Fetch a supplier feed and apply create-full / update-whitelist."""
    adapter = ADAPTERS.get(supplier_code)
    if adapter is None:
        typer.echo(f"Unknown supplier '{supplier_code}'. Known: {', '.join(ADAPTERS)}")
        raise typer.Exit(code=1)

    with session_scope() as session:
        supplier = (
            session.query(Supplier).filter_by(code=supplier_code).one_or_none()
        )
        if supplier is None:
            typer.echo(f"Supplier '{supplier_code}' not in DB. Seed it first.")
            raise typer.Exit(code=1)
        raw = adapter.fetch(supplier.feed_url)
        parsed = adapter.parse(raw)
        stats = run_sync(session, supplier, parsed)
    typer.echo(f"Sync done: {stats}")


if __name__ == "__main__":
    app()
```

- [ ] **Step 2: Verify the CLI wires up (shows help without touching the DB)**

Run:
```bash
cd poolzoneV2 && ./.venv/bin/poolz sync --help
```
Expected: Typer help text for the `sync` command, listing the `supplier_code` argument.

- [ ] **Step 3: Commit**

```bash
git add poolzoneV2/app/cli.py
git commit -m "feat(v2): poolz sync CLI entry point"
```

---

### Task 10: Full-suite green + README

**Files:**
- Create: `poolzoneV2/README.md`

- [ ] **Step 1: Run the whole suite**

Run:
```bash
cd poolzoneV2 && ./.venv/bin/pytest -q
```
Expected: `10 passed` (6 parse + 4 pipeline).

- [ ] **Step 2: Format with ruff**

Run:
```bash
cd poolzoneV2 && ./.venv/bin/ruff format app tests && ./.venv/bin/ruff check app tests
```
Expected: files formatted; `ruff check` reports `All checks passed!` (or fix the few it flags).

- [ ] **Step 3: Write `poolzoneV2/README.md`**

```markdown
# Poolzone Middleware v2

Clean-restart rebuild. See `../docs/superpowers/specs/2026-07-02-poolzone-middleware-v2-design.md`.

## First-time setup

    python3.12 -m venv .venv
    ./.venv/bin/pip install -e ".[dev]"
    cp .env.example .env
    docker compose up -d
    ./.venv/bin/alembic upgrade head

## Test

    ./.venv/bin/pytest -q

## Sync a supplier (after seeding a `suppliers` row)

    ./.venv/bin/poolz sync pooltechnika

## Status

Plan 1 (foundation + sync) complete. Next: Plan 2 (pricing + Upgates XML export).
```

- [ ] **Step 4: Commit**

```bash
git add poolzoneV2/README.md
git commit -m "docs(v2): README + plan 1 complete"
```

---

## What this plan deliberately leaves for later plans

- **Category resolution during sync.** `supplier_category_map` and `categories` exist as tables, but the pipeline does not yet link products to categories (the map is empty until Plan 4 bootstrap seeds it). Add category linking to `run_sync` in Plan 4, once the mapping is populated. Tracked so it is not forgotten.
- **Pricing math + `AK` prefix = Aseko rule.** The old script picks the Aseko margin by `ITEM_ID.startswith("AK")`, *not* by the `MANUFACTURER` field. Plan 2 must implement the manufacturer-scope pricing rule keyed on code prefix, not the manufacturer column. Captured here so the detail survives.
- **Upgates XML export, pricing rules, FastAPI, React, bootstrap** — Plans 2–4.

---

## Self-Review

- **Spec coverage (this plan's slice):** §3 single process foundation ✓ (Tasks 1–3, 5), §4 all 9 tables ✓ (Task 4), §5 create-full/update-whitelist ✓ (Task 8), §5 adapter fetch/parse ✓ (Task 7), §10 overlap guard ✓ (Task 8 in-progress check), §4 `job_runs` audit ✓ (Task 8). Pricing/export/GUI/bootstrap are explicitly out of this plan's scope.
- **Type consistency:** `ParsedProduct` fields used in Task 8 (`title, ean, manufacturer, price_purchase, stock, weight, availability, image_urls, params`) all defined in Task 7. `run_sync(session, supplier, parsed_products)` signature matches its call in Task 9. `Supplier.update_whitelist` default matches the whitelist fallback in the pipeline.
- **Placeholder scan:** none — every code step has full code; every run step has an expected result.
