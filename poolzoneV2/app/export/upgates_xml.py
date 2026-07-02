from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Category, JobRun, Product, ProductCategory
from app.pricing import load_margin_rules, resolve_margin

PRODUCTS_FILE = "poolzone_products.xml"


def _sub(parent: ET.Element, tag: str, text) -> ET.Element:
    el = ET.SubElement(parent, tag)
    if text is not None:
        el.text = str(text)
    return el


def _category_map(session: Session, product_ids: list[int]) -> dict[int, list[tuple[str, bool]]]:
    """All (code, primary) per product in one query, ordered by position."""
    out: dict[int, list[tuple[str, bool]]] = defaultdict(list)
    if not product_ids:
        return out
    rows = session.execute(
        select(ProductCategory.product_id, Category.upgates_code, ProductCategory.primary_yn)
        .join(Category, ProductCategory.category_id == Category.id)
        .where(ProductCategory.product_id.in_(product_ids))
        .order_by(ProductCategory.position)
    ).all()
    for pid, code, primary in rows:
        if code:
            out[pid].append((code, primary))
    return out


def render_products(session: Session, rules: dict) -> tuple[bytes, int]:
    """Render active products to Upgates PRODUCTS XML. EAN blanked, value carried in SUPPLIER_CODE.

    Returns (xml_bytes, product_count).
    """
    root = ET.Element("PRODUCTS", {"version": "1.0"})
    products = (
        session.execute(
            select(Product).where(Product.active.is_(True)).options(selectinload(Product.images))
        )
        .scalars()
        .all()
    )
    cat_map = _category_map(session, [p.id for p in products])
    for p in products:
        prod = ET.SubElement(root, "PRODUCT")
        _sub(prod, "CODE", p.code)

        descriptions = ET.SubElement(prod, "DESCRIPTIONS")
        desc = ET.SubElement(descriptions, "DESCRIPTION", {"language": "cs"})
        if p.title:
            _sub(desc, "TITLE", p.title)
        if p.url_slug:
            _sub(desc, "URL", p.url_slug)

        if p.images:
            images = ET.SubElement(prod, "IMAGES")
            for img in sorted(p.images, key=lambda i: i.ord):
                _sub(ET.SubElement(images, "IMAGE"), "URL", img.url)

        if p.price_purchase is not None:
            prices = ET.SubElement(prod, "PRICES")
            price = ET.SubElement(prices, "PRICE", {"language": "cs"})
            # Reproduce the legacy script's float math + str() formatting exactly.
            purchase = float(p.price_purchase)
            margin = float(resolve_margin(p, rules))
            common = str(purchase * (1 / (1 - margin)) * float(p.coefficient))
            _sub(price, "PRICE_PURCHASE", str(purchase))
            _sub(price, "PRICE_COMMON", common)
            pricelist = ET.SubElement(ET.SubElement(price, "PRICELISTS"), "PRICELIST")
            _sub(pricelist, "PRICE_ORIGINAL", common)

        cats = cat_map.get(p.id, [])
        if cats:
            categories = ET.SubElement(prod, "CATEGORIES")
            for code, primary in cats:
                cat_el = ET.SubElement(categories, "CATEGORY")
                _sub(cat_el, "CODE", code)
                _sub(cat_el, "PRIMARY_YN", "true" if primary else "false")

        ET.SubElement(prod, "EAN")  # deliberately empty — a filled EAN breaks price comparators
        if p.ean:
            _sub(prod, "SUPPLIER_CODE", p.ean)
        if p.stock is not None:
            _sub(prod, "STOCK", p.stock)
        if p.weight is not None:
            _sub(prod, "WEIGHT", p.weight)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True), len(products)


def run_export(session: Session, out_dir) -> dict:
    """Render products, skip if unchanged since last export, else write file + record JobRun."""
    rules = load_margin_rules(session)
    xml, count = render_products(session, rules)
    digest = hashlib.sha256(xml).hexdigest()

    last = (
        session.execute(
            select(JobRun)
            .where(JobRun.kind == "export", JobRun.status == "success")
            .order_by(JobRun.id.desc())
        )
        .scalars()
        .first()
    )
    if last and last.stats.get("hash") == digest:
        return {"skipped": True, "hash": digest}

    out_path = Path(out_dir) / PRODUCTS_FILE
    out_path.write_bytes(xml)

    stats = {"products": count, "hash": digest, "path": str(out_path)}
    session.add(
        JobRun(
            kind="export",
            status="success",
            finished_at=datetime.now(timezone.utc),
            stats=stats,
        )
    )
    session.flush()
    return stats
