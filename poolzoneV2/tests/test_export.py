import xml.etree.ElementTree as ET
from decimal import Decimal

from app.export.upgates_xml import render_products, run_export
from app.models import (
    Category,
    JobRun,
    PricingRule,
    Product,
    ProductCategory,
    ProductImage,
    Supplier,
)


def _seed(db_session, active=True):
    db_session.add(PricingRule(scope="default", match_value=None, margin_pct=Decimal("0.35")))
    s = Supplier(code="pooltechnika", name="P")
    db_session.add(s)
    db_session.flush()
    cat = Category(name="Náhradní díly", upgates_code="poolzone|nahradni-dily")
    db_session.add(cat)
    db_session.flush()
    p = Product(
        code="ESPA1",
        supplier_id=s.id,
        title="Těsnění",
        url_slug="https://www.pooltechnika.cz/tesneni",
        ean="8594",
        price_purchase=Decimal("77.00"),
        margin_pct=Decimal("0.35"),
        coefficient=Decimal("1.0"),
        stock=7,
        weight=6,
        active=active,
    )
    p.images = [ProductImage(url="http://img/1.jpg", ord=0)]
    db_session.add(p)
    db_session.flush()
    db_session.add(ProductCategory(product_id=p.id, category_id=cat.id, primary_yn=True))
    db_session.flush()
    return p


def test_render_products_shape_and_price(db_session):
    from app.pricing import load_margin_rules

    _seed(db_session)
    xml, count = render_products(db_session, load_margin_rules(db_session))
    assert count == 1
    root = ET.fromstring(xml)
    assert root.tag == "PRODUCTS"
    prod = root.find("PRODUCT")
    assert prod.findtext("CODE") == "ESPA1"
    assert prod.find("DESCRIPTIONS/DESCRIPTION").get("language") == "cs"
    assert prod.findtext("DESCRIPTIONS/DESCRIPTION/TITLE") == "Těsnění"
    # 77 / 0.65 = 118.46
    assert prod.findtext("PRICES/PRICE/PRICE_COMMON") == "118.46"
    assert prod.findtext("PRICES/PRICE/PRICE_PURCHASE") == "77.00"
    assert prod.findtext("PRICES/PRICE/PRICELISTS/PRICELIST/PRICE_ORIGINAL") == "118.46"
    # EAN element empty, EAN value carried in SUPPLIER_CODE (old convention)
    assert prod.findtext("EAN") in (None, "")
    assert prod.findtext("SUPPLIER_CODE") == "8594"
    assert prod.findtext("STOCK") == "7"
    assert prod.findtext("WEIGHT") == "6"
    cat = prod.find("CATEGORIES/CATEGORY")
    assert cat.findtext("CODE") == "poolzone|nahradni-dily"
    assert cat.findtext("PRIMARY_YN") == "true"


def test_render_skips_inactive_products(db_session):
    from app.pricing import load_margin_rules

    _seed(db_session, active=False)
    xml, count = render_products(db_session, load_margin_rules(db_session))
    assert count == 0
    assert ET.fromstring(xml).find("PRODUCT") is None


def test_run_export_writes_file_and_records_job(db_session, tmp_path):
    _seed(db_session)
    stats = run_export(db_session, tmp_path)
    assert (tmp_path / "poolzone_products.xml").exists()
    assert stats["products"] == 1
    job = db_session.query(JobRun).filter_by(kind="export").order_by(JobRun.id.desc()).first()
    assert job.status == "success"
    assert job.stats["hash"]


def test_run_export_skips_when_unchanged(db_session, tmp_path):
    _seed(db_session)
    run_export(db_session, tmp_path)
    stats2 = run_export(db_session, tmp_path)
    assert stats2["skipped"] is True
