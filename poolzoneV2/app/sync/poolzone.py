"""Import the poolzone.cz live Upgates exports (products + categories).

The eshop is the master for content: this refreshes the middleware DB from the
live XML feeds. Matching is by business key (`code` for products, `upgates_code`
for categories) — NOT supplier-scoped, since this is eshop-native data.

Whitelist controls what an import may overwrite on an EXISTING row. A brand-new
row always gets every field (whitelist governs clobbering, not creation).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import requests
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Category, Product, ProductCategory, ProductImage, ProductParam

# Canonical whitelist options surfaced in the GUI. Order = display order.
# ponytail: no purchase price — the live export omits PRICE_PURCHASE (sale prices
# only), and sale is derived from supplier purchase price, so it is never imported.
PRODUCT_FIELDS = [
    "title",
    "short_description",
    "long_description",
    "ean",
    "manufacturer",
    "availability",
    "stock",
    "weight",
    "active",
    "images",
    "params",
    "categories",
]
CATEGORY_FIELDS = ["name", "seo_title", "seo_description", "parent"]

DEFAULT_PRODUCTS_URL = "https://www.poolzone.cz/export-full-products-CmZBRQh40G.xml"
DEFAULT_CATEGORIES_URL = "https://www.poolzone.cz/export-categories-hKyCWM00YG.xml"


def fetch(url: str) -> bytes:
    """Network boundary — kept trivial and mockable."""
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    return resp.content


def _text(el: ET.Element | None, path: str) -> str | None:
    if el is None:
        return None
    found = el.findtext(path)
    if found is None:
        return None
    val = found.strip()
    return val or None


def _int(text: str | None) -> int | None:
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _yn(text: str | None) -> bool:
    # Upgates writes "1"/"0"; some exports use "true"/"false".
    return (text or "").strip().lower() in ("1", "true", "yes")


# --- parsers (pure, testable without IO) ------------------------------------


def parse_products(raw: bytes) -> list[dict]:
    root = ET.fromstring(raw)
    out: list[dict] = []
    for p in root.findall("PRODUCT"):
        code = _text(p, "CODE")
        if not code:
            continue
        # ponytail: first DESCRIPTION — the feed carries only the cz language.
        out.append(
            {
                "code": code,
                "title": _text(p, "DESCRIPTIONS/DESCRIPTION/TITLE"),
                "short_description": _text(p, "DESCRIPTIONS/DESCRIPTION/SHORT_DESCRIPTION"),
                "long_description": _text(p, "DESCRIPTIONS/DESCRIPTION/LONG_DESCRIPTION"),
                "ean": _text(p, "EAN"),
                "manufacturer": _text(p, "MANUFACTURER"),
                "availability": _text(p, "AVAILABILITY"),
                "stock": _int(p.findtext("STOCK")),
                "weight": _int(p.findtext("WEIGHT")),
                "active": _yn(p.findtext("ACTIVE_YN")),
                "images": [u.text.strip() for u in p.findall("IMAGES/IMAGE/URL") if u.text and u.text.strip()],
                "params": [
                    (n, (v or "").strip())
                    for param in p.findall("PARAMETERS/PARAMETER")
                    if (n := (param.findtext("NAME") or "").strip())
                    for v in [param.findtext("VALUE")]
                ],
                "categories": [
                    {
                        "code": c.findtext("CODE").strip(),
                        "primary": _yn(c.findtext("PRIMARY_YN")),
                        "position": _int(c.findtext("POSITION")) or 0,
                    }
                    for c in p.findall("CATEGORIES/CATEGORY")
                    if c.findtext("CODE")
                ],
            }
        )
    return out


def parse_categories(raw: bytes) -> list[dict]:
    root = ET.fromstring(raw)
    out: list[dict] = []
    for c in root.findall("CATEGORY"):
        code = _text(c, "CODE")
        if not code:
            continue
        out.append(
            {
                "code": code,
                "ext_id": _text(c, "CATEGORY_ID"),
                "parent_ext_id": _text(c, "PARENT_ID"),
                "name": _text(c, "DESCRIPTIONS/DESCRIPTION/NAME"),
                "seo_title": _text(c, "SEO_OPTIMALIZATION/SEO/SEO_TITLE"),
                "seo_description": _text(c, "SEO_OPTIMALIZATION/SEO/SEO_META_DESCRIPTION"),
            }
        )
    return out


# --- importers (whitelist-aware upsert) -------------------------------------

_PRODUCT_SCALARS = (
    "title",
    "short_description",
    "long_description",
    "ean",
    "manufacturer",
    "availability",
    "stock",
    "weight",
    "active",
)


def _apply_product(
    product: Product, spec: dict, fields: set[str], cat_by_code: dict[str, int], session: Session
) -> None:
    for f in _PRODUCT_SCALARS:
        if f in fields:
            setattr(product, f, spec[f])
    if "images" in fields:
        product.images = [ProductImage(url=u, ord=i) for i, u in enumerate(spec["images"])]
    if "params" in fields:
        product.params = [
            ProductParam(name=n, value=v, ord=i) for i, (n, v) in enumerate(spec["params"])
        ]
    if "categories" in fields:
        if product.id is not None:  # existing row: clear old links first
            session.execute(delete(ProductCategory).where(ProductCategory.product_id == product.id))
        else:
            session.add(product)
            session.flush()  # need product.id for the link rows
        seen: set[int] = set()
        for c in spec["categories"]:
            cid = cat_by_code.get(c["code"])
            if cid is None or cid in seen:
                continue
            seen.add(cid)
            session.add(
                ProductCategory(
                    product_id=product.id,
                    category_id=cid,
                    primary_yn=c["primary"],
                    position=c["position"],
                )
            )


def import_products(session: Session, raw: bytes, whitelist: list[str]) -> dict:
    cat_by_code = {
        c.upgates_code: c.id for c in session.execute(select(Category)).scalars() if c.upgates_code
    }
    all_fields = set(PRODUCT_FIELDS)
    wl = set(whitelist)
    stats = {"products_seen": 0, "created": 0, "updated": 0, "errors": []}
    for spec in parse_products(raw):
        stats["products_seen"] += 1
        try:
            # Match by code across all suppliers — the eshop code is the real key.
            # ponytail: first match wins; refine if duplicate codes across suppliers appear.
            existing = session.execute(
                select(Product).where(Product.code == spec["code"])
            ).scalars().first()
            if existing is None:
                product = Product(code=spec["code"])
                _apply_product(product, spec, all_fields, cat_by_code, session)
                session.add(product)
                stats["created"] += 1
            else:
                _apply_product(existing, spec, wl, cat_by_code, session)
                stats["updated"] += 1
            session.flush()
        except Exception as exc:  # per-row isolation: one bad row never aborts the run
            stats["errors"].append({"code": spec["code"], "error": str(exc)})
    return stats


def import_categories(session: Session, raw: bytes, whitelist: list[str]) -> dict:
    wl = set(whitelist)
    specs = parse_categories(raw)
    stats = {"categories_seen": len(specs), "created": 0, "updated": 0, "errors": []}
    by_ext: dict[str, Category] = {}
    created_codes: set[str] = set()

    # Pass 1: upsert by upgates_code (scalars).
    for spec in specs:
        try:
            cat = session.execute(
                select(Category).where(Category.upgates_code == spec["code"])
            ).scalar_one_or_none()
            if cat is None:
                cat = Category(
                    upgates_code=spec["code"],
                    name=spec["name"] or spec["code"],
                    seo_title=spec["seo_title"],
                    seo_description=spec["seo_description"],
                )
                session.add(cat)
                stats["created"] += 1
                created_codes.add(spec["code"])
            else:
                if "name" in wl and spec["name"]:
                    cat.name = spec["name"]
                if "seo_title" in wl:
                    cat.seo_title = spec["seo_title"]
                if "seo_description" in wl:
                    cat.seo_description = spec["seo_description"]
                stats["updated"] += 1
            if spec["ext_id"]:
                by_ext[spec["ext_id"]] = cat
        except Exception as exc:
            stats["errors"].append({"code": spec["code"], "error": str(exc)})
    session.flush()

    # Pass 2: wire parents now that every category exists (new rows always, existing
    # only when "parent" is whitelisted).
    for spec in specs:
        cat = by_ext.get(spec["ext_id"]) if spec["ext_id"] else None
        if cat is None:
            continue
        if "parent" in wl or spec["code"] in created_codes:
            parent = by_ext.get(spec["parent_ext_id"]) if spec["parent_ext_id"] else None
            cat.parent_id = parent.id if parent else None
    session.flush()
    return stats
