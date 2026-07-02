from decimal import Decimal

from app.models import Category, Product, ProductCategory, Supplier, SupplierCategoryMap
from scripts.bootstrap import (
    apply_pricing,
    load_categories,
    load_products,
    parse_upgates_products,
    pricing_margin,
)

PRODUCTS_XML = b"""<?xml version="1.0"?>
<PRODUCTS version="1.0">
  <PRODUCT>
    <CODE>AK13327</CODE>
    <DESCRIPTIONS><DESCRIPTION language="cs"><TITLE>OXY 5L</TITLE><URL>https://x/oxy</URL></DESCRIPTION></DESCRIPTIONS>
    <IMAGES><IMAGE><URL>http://img/1.jpg</URL></IMAGE></IMAGES>
    <PRICES><PRICE language="cs"><PRICE_PURCHASE>77.0</PRICE_PURCHASE><PRICE_COMMON>118.46</PRICE_COMMON></PRICE></PRICES>
    <CATEGORIES>
      <CATEGORY><CODE>poolzone|chemie</CODE><PRIMARY_YN>true</PRIMARY_YN></CATEGORY>
    </CATEGORIES>
    <EAN /><SUPPLIER_CODE>8594</SUPPLIER_CODE><STOCK>7</STOCK><WEIGHT>6</WEIGHT>
  </PRODUCT>
</PRODUCTS>"""

CATEGORY_ROWS = [
    {
        "name": "Chemie",
        "code": "poolzone|chemie",
        "ext_id": "A1",
        "parent_ext_id": None,
        "seo_title": "Chemie SEO",
        "seo_description": "desc",
        "supplier_paths": ["Chemie | pH", "Chemie | Kyslíková"],
    },
    {
        "name": "pH",
        "code": "poolzone|chemie|ph",
        "ext_id": "A2",
        "parent_ext_id": "A1",
        "seo_title": None,
        "seo_description": None,
        "supplier_paths": [],
    },
]


def test_parse_upgates_products():
    specs = parse_upgates_products(PRODUCTS_XML)
    assert len(specs) == 1
    s = specs[0]
    assert s["code"] == "AK13327"
    assert s["title"] == "OXY 5L"
    assert s["ean"] == "8594"
    assert s["price_purchase"] == Decimal("77.00")
    assert s["stock"] == 7
    assert s["weight"] == 6
    assert s["images"] == ["http://img/1.jpg"]
    assert s["categories"] == [("poolzone|chemie", True)]


def test_pricing_margin_prefix():
    assert pricing_margin("AK1") == Decimal("0.35")
    assert pricing_margin("ESPA1") == Decimal("0.45")


def _supplier(db):
    s = Supplier(code="pooltechnika", name="P")
    db.add(s)
    db.flush()
    return s


def test_load_categories_wires_parents_and_supplier_map(db_session):
    supplier = _supplier(db_session)
    created = load_categories(db_session, supplier, CATEGORY_ROWS)
    assert created == 2
    child = db_session.query(Category).filter_by(upgates_code="poolzone|chemie|ph").one()
    parent = db_session.query(Category).filter_by(upgates_code="poolzone|chemie").one()
    assert child.parent_id == parent.id
    paths = {m.supplier_path for m in db_session.query(SupplierCategoryMap)}
    assert paths == {"Chemie | pH", "Chemie | Kyslíková"}


def test_load_categories_idempotent(db_session):
    supplier = _supplier(db_session)
    load_categories(db_session, supplier, CATEGORY_ROWS)
    assert load_categories(db_session, supplier, CATEGORY_ROWS) == 0  # nothing new second run
    assert db_session.query(Category).count() == 2


def test_load_products_links_categories(db_session):
    supplier = _supplier(db_session)
    load_categories(db_session, supplier, CATEGORY_ROWS)
    created = load_products(db_session, supplier, PRODUCTS_XML)
    assert created == 1
    prod = db_session.query(Product).filter_by(code="AK13327").one()
    link = db_session.query(ProductCategory).filter_by(product_id=prod.id).one()
    assert link.primary_yn is True


def test_apply_pricing_sets_margin_and_coefficient(db_session):
    supplier = _supplier(db_session)
    load_products(db_session, supplier, PRODUCTS_XML)
    updated = apply_pricing(
        db_session, [{"code": "AK13327", "coefficient": Decimal("0.995"), "note": "Sleva=0.05%"}]
    )
    assert updated == 1
    prod = db_session.query(Product).filter_by(code="AK13327").one()
    assert prod.coefficient == Decimal("0.9950")
    assert prod.margin_pct == Decimal("0.3500")  # AK prefix
    assert prod.note == "Sleva=0.05%"
