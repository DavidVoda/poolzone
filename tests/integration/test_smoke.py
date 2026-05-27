from decimal import Decimal

from libpoolzone.catalog import categories as cats_svc
from libpoolzone.catalog import locks as locks_svc
from libpoolzone.catalog import products as products_svc
from libpoolzone.storage.models import Product


def test_locked_field_survives_supplier_sync_simulation(db_session):
    # 1. Initial product setup as if bootstrapped from Upgates export
    p = products_svc.create_product(
        db_session,
        code="AK1234",
        titles={"cs": "Čerpadlo Aseko Premium"},
        long_descriptions={"cs": "<p>Manually edited copy</p>"},
        price_purchase=Decimal("1000"),
        price_common=Decimal("2000"),
        stock=5,
    )

    # 2. Human locks the long description (e.g. accepted an AI suggestion)
    locks_svc.lock_field(
        db_session, product_id=p.id, field_path="descriptions.cs.long", locked_by="david"
    )

    # 3. Simulate a Pooltechnika sync that would update price + description + stock
    incoming_changes = {
        "long_descriptions": {"cs": "<p>Supplier generic description</p>"},
        "price_purchase": Decimal("1100"),
        "stock": 12,
    }
    field_path_for = {
        "long_descriptions": "descriptions.cs.long",
        "price_purchase": "price.purchase",
        "stock": "stock",
    }
    stats = locks_svc.apply_changes_respecting_locks(
        db_session,
        product_id=p.id,
        changes=incoming_changes,
        field_path_for=field_path_for,
    )

    # 4. Assert: description preserved, other fields updated
    refreshed = db_session.get(Product, p.id)
    assert refreshed.long_descriptions == {"cs": "<p>Manually edited copy</p>"}
    assert refreshed.price_purchase == Decimal("1100")
    assert refreshed.stock == 12
    assert stats == {"updated": 2, "locked_skips": 1}


def test_product_can_have_primary_category(db_session):
    cat_root = cats_svc.create_category(db_session, code="root", name_i18n={"cs": "Root"})
    cat_child = cats_svc.create_category(
        db_session, code="pumps", name_i18n={"cs": "Čerpadla"}, parent_id=cat_root.id
    )

    p = products_svc.create_product(db_session, code="P_E2E", titles={"cs": "E2E"})

    cats_svc.link_product(db_session, product_id=p.id, category_id=cat_child.id, primary_yn=True)
    cats_svc.link_product(db_session, product_id=p.id, category_id=cat_root.id, primary_yn=False)

    refreshed = db_session.get(Product, p.id)
    # Sanity: product exists and categories don't crash
    assert refreshed.code == "P_E2E"
