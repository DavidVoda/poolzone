from decimal import Decimal

from app.models import Product, ProductImage, ProductParam, Supplier
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
    assert prod.title == "OWNER EDIT"  # NOT overwritten (not in whitelist)
    assert prod.stock == 99  # whitelisted -> updated
    assert prod.price_purchase == Decimal("222.00")  # whitelisted -> updated


def test_existing_product_images_and_params_not_resynced(db_session):
    supplier = _supplier(db_session)
    run_sync(db_session, supplier, [_parsed("AK1")])
    run_sync(
        db_session, supplier, [_parsed("AK1", image_urls=["http://img/2.jpg", "http://img/3.jpg"])]
    )

    prod = db_session.query(Product).filter_by(code="AK1").one()
    urls = {i.url for i in db_session.query(ProductImage).filter_by(product_id=prod.id)}
    assert urls == {"http://img/1.jpg"}  # original image kept, not replaced


def test_run_returns_stats_and_stamps_supplier(db_session):
    # run_sync is a pure upsert now — the caller (router/CLI) owns the JobRun via job_run.
    supplier = _supplier(db_session)
    stats = run_sync(db_session, supplier, [_parsed("AK1"), _parsed("AK2")])
    assert stats["products_seen"] == 2
    assert stats["created"] == 2
    assert supplier.last_synced_at is not None


def test_resync_same_feed_counts_unchanged_not_updated(db_session):
    # Re-running the identical feed must NOT report every product as "updated"
    # (regression: it used to count every existing row regardless of change).
    supplier = _supplier(db_session)
    run_sync(db_session, supplier, [_parsed("AK1"), _parsed("AK2")])

    stats = run_sync(db_session, supplier, [_parsed("AK1"), _parsed("AK2")])
    assert stats["created"] == 0
    assert stats["updated"] == 0
    assert stats["unchanged"] == 2

    # A real whitelisted change flips it back to updated.
    stats = run_sync(db_session, supplier, [_parsed("AK1", stock=999), _parsed("AK2")])
    assert stats["updated"] == 1
    assert stats["unchanged"] == 1
