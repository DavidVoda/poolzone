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
