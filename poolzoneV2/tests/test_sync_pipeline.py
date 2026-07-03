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


def test_run_records_job_run(db_session):
    supplier = _supplier(db_session)
    run_sync(db_session, supplier, [_parsed("AK1"), _parsed("AK2")])
    job = db_session.query(JobRun).filter_by(kind="sync").order_by(JobRun.id.desc()).first()
    assert job.status == "success"
    assert job.stats["products_seen"] == 2
    assert job.stats["created"] == 2
