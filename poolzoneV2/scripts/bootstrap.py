"""One-time bootstrap: load current Upgates products + category/pricing Excels into the DB.

Idempotent — safe to re-run. Reads the legacy files from the repo root by default.
Order matters: categories (+ supplier map) first, then products (link categories),
then pricing (set coefficient/margin on matching products).

    ./.venv/bin/python -m scripts.bootstrap            # uses ../<file> defaults
    ./.venv/bin/python -m scripts.bootstrap --root /path/to/legacy/files
"""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import session_scope
from app.models import (
    Category,
    PricingRule,
    Product,
    ProductCategory,
    ProductImage,
    Supplier,
    SupplierCategoryMap,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SUPPLIER_CODE = "pooltechnika"


# --- pure parsers (testable without IO) -------------------------------------


def parse_upgates_products(raw: bytes) -> list[dict]:
    """Parse a poolzone_products.xml (Upgates PRODUCT format) into plain dicts."""
    root = ET.fromstring(raw)
    out: list[dict] = []
    for p in root.findall("PRODUCT"):
        code = p.findtext("CODE")
        if not code:
            continue
        price_text = p.findtext("PRICES/PRICE/PRICE_PURCHASE")
        try:
            price = Decimal(price_text).quantize(Decimal("0.01")) if price_text else None
        except InvalidOperation:
            price = None
        cats = [
            (c.findtext("CODE"), (c.findtext("PRIMARY_YN") or "").lower() == "true")
            for c in p.findall("CATEGORIES/CATEGORY")
            if c.findtext("CODE")
        ]
        out.append(
            {
                "code": code.strip(),
                "title": p.findtext("DESCRIPTIONS/DESCRIPTION/TITLE"),
                "url_slug": p.findtext("DESCRIPTIONS/DESCRIPTION/URL"),
                "ean": p.findtext("SUPPLIER_CODE"),
                "price_purchase": price,
                "stock": _int(p.findtext("STOCK")),
                "weight": _int(p.findtext("WEIGHT")),
                "images": [u.text for u in p.findall("IMAGES/IMAGE/URL") if u.text],
                "categories": cats,
            }
        )
    return out


def _int(text: str | None) -> int | None:
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def pricing_margin(code: str) -> Decimal:
    """Reproduce the old 'listed in Excel' base margin: Aseko (AK prefix) 0.35, else 0.45."""
    return Decimal("0.35") if code.startswith("AK") else Decimal("0.45")


# --- Excel readers ----------------------------------------------------------


def _rows(xlsx_path: Path) -> list[dict]:
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(it)]
    return [dict(zip(header, row)) for row in it]


def category_rows(xlsx_path: Path) -> list[dict]:
    return [
        {
            "name": r.get("Název kategorie"),
            "code": r.get("Kód kategorie"),
            "ext_id": r.get("ID kategorie"),
            "parent_ext_id": r.get("ID nadřazené kategorie"),
            "seo_title": r.get("SEO_TITLE"),
            "seo_description": r.get("SEO_META_DESCRIPTION"),
            "supplier_paths": [
                s.strip()
                for s in str(r.get("Pooltechnika ID kategorie") or "").split(";")
                if s.strip()
            ],
        }
        for r in _rows(xlsx_path)
        if r.get("Kód kategorie") and r.get("Název kategorie")
    ]


def pricing_rows(xlsx_path: Path) -> list[dict]:
    out = []
    for r in _rows(xlsx_path):
        code = r.get("Kód")
        coef = r.get("Koeficient")
        if not code or coef is None:
            continue
        note_bits = [f"{k}={r[k]}" for k in ("Sleva", "Příplatek") if r.get(k) not in (None, "")]
        out.append(
            {
                "code": str(code).strip(),
                "coefficient": Decimal(str(coef)),
                "note": "; ".join(note_bits) or None,
            }
        )
    return out


# --- DB loaders (idempotent) ------------------------------------------------


def load_categories(session: Session, supplier: Supplier, rows: list[dict]) -> int:
    by_ext: dict[str, Category] = {}
    created = 0
    for r in rows:
        cat = session.execute(
            select(Category).where(Category.upgates_code == r["code"])
        ).scalar_one_or_none()
        if cat is None:
            cat = Category(
                name=r["name"],
                upgates_code=r["code"],
                seo_title=r["seo_title"],
                seo_description=r["seo_description"],
            )
            session.add(cat)
            created += 1
        if r["ext_id"] is not None:
            by_ext[str(r["ext_id"])] = cat
    session.flush()

    # Second pass: wire parents + supplier-path map now that every category exists.
    # A supplier_path maps to ONE category (unique constraint). The Excel repeats
    # paths across rows — first occurrence wins.
    seen_paths = {
        m.supplier_path
        for m in session.execute(
            select(SupplierCategoryMap).where(SupplierCategoryMap.supplier_id == supplier.id)
        ).scalars()
    }
    for r in rows:
        cat = by_ext.get(str(r["ext_id"]))
        if cat is None:
            continue
        parent = by_ext.get(str(r["parent_ext_id"])) if r["parent_ext_id"] is not None else None
        cat.parent_id = parent.id if parent else None
        for path in r["supplier_paths"]:
            if path in seen_paths:
                continue
            seen_paths.add(path)
            session.add(
                SupplierCategoryMap(supplier_id=supplier.id, supplier_path=path, category_id=cat.id)
            )
    session.flush()
    return created


def load_products(session: Session, supplier: Supplier, raw: bytes) -> int:
    cat_by_code = {
        c.upgates_code: c.id for c in session.execute(select(Category)).scalars() if c.upgates_code
    }
    created = 0
    for spec in parse_upgates_products(raw):
        exists = session.execute(
            select(Product).where(Product.supplier_id == supplier.id, Product.code == spec["code"])
        ).scalar_one_or_none()
        if exists is not None:
            continue
        product = Product(
            code=spec["code"],
            supplier_id=supplier.id,
            title=spec["title"],
            url_slug=spec["url_slug"],
            ean=spec["ean"],
            price_purchase=spec["price_purchase"],
            stock=spec["stock"],
            weight=spec["weight"],
            active=True,
        )
        product.images = [ProductImage(url=u, ord=i) for i, u in enumerate(spec["images"])]
        session.add(product)
        session.flush()
        for pos, (code, primary) in enumerate(spec["categories"]):
            cid = cat_by_code.get(code)
            if cid:
                session.add(
                    ProductCategory(
                        product_id=product.id, category_id=cid, primary_yn=primary, position=pos
                    )
                )
        created += 1
    session.flush()
    return created


def apply_pricing(session: Session, rows: list[dict]) -> int:
    updated = 0
    for r in rows:
        product = session.execute(
            select(Product).where(Product.code == r["code"])
        ).scalar_one_or_none()
        if product is None:
            continue
        product.coefficient = r["coefficient"]
        product.margin_pct = pricing_margin(product.code)
        if r["note"]:
            product.note = r["note"]
        updated += 1
    session.flush()
    return updated


def ensure_default_rules(session: Session) -> None:
    if session.execute(select(PricingRule)).first():
        return
    session.add(PricingRule(scope="default", match_value=None, margin_pct=Decimal("0.35")))
    session.add(PricingRule(scope="manufacturer", match_value="AK", margin_pct=Decimal("0.34")))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=REPO_ROOT)
    args = ap.parse_args()

    with session_scope() as session:
        supplier = session.execute(
            select(Supplier).where(Supplier.code == SUPPLIER_CODE)
        ).scalar_one_or_none()
        if supplier is None:
            supplier = Supplier(code=SUPPLIER_CODE, name="Pooltechnika")
            session.add(supplier)
            session.flush()

        ensure_default_rules(session)
        cats = load_categories(
            session, supplier, category_rows(args.root / "poolzone_categories.xlsx")
        )
        prods = load_products(session, supplier, (args.root / "poolzone_products.xml").read_bytes())
        priced = apply_pricing(session, pricing_rows(args.root / "produkty_cenotvorba.xlsx"))
        print(f"categories +{cats}, products +{prods}, priced {priced}")


if __name__ == "__main__":
    main()
