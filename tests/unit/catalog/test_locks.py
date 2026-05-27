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
