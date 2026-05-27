from libpoolzone.catalog import categories as cats_svc
from libpoolzone.catalog import products as products_svc
from libpoolzone.storage.models import ProductCategory


def test_create_category_persists(db_session):
    cat = cats_svc.create_category(
        db_session,
        code="cat_pumps",
        name_i18n={"cs": "Čerpadla"},
    )
    assert cat.id is not None
    assert cat.code == "cat_pumps"
    assert cat.name_i18n == {"cs": "Čerpadla"}


def test_create_subcategory_links_parent(db_session):
    parent = cats_svc.create_category(db_session, code="root", name_i18n={"cs": "Root"})
    child = cats_svc.create_category(
        db_session, code="child", name_i18n={"cs": "Child"}, parent_id=parent.id
    )
    db_session.flush()
    db_session.refresh(parent)
    assert child.parent_id == parent.id
    assert child in parent.children


def test_link_product_to_category_with_primary(db_session):
    cat = cats_svc.create_category(db_session, code="c1", name_i18n={"cs": "C1"})
    p = products_svc.create_product(db_session, code="P1", titles={"cs": "P"})

    cats_svc.link_product(db_session, product_id=p.id, category_id=cat.id, primary_yn=True)

    link = (
        db_session.query(ProductCategory)
        .filter_by(product_id=p.id, category_id=cat.id)
        .one()
    )
    assert link.primary_yn is True


def test_link_product_twice_is_idempotent(db_session):
    cat = cats_svc.create_category(db_session, code="c2", name_i18n={"cs": "C2"})
    p = products_svc.create_product(db_session, code="P2", titles={"cs": "P"})

    cats_svc.link_product(db_session, product_id=p.id, category_id=cat.id, primary_yn=False)
    cats_svc.link_product(db_session, product_id=p.id, category_id=cat.id, primary_yn=True)

    links = (
        db_session.query(ProductCategory)
        .filter_by(product_id=p.id, category_id=cat.id)
        .all()
    )
    assert len(links) == 1
    assert links[0].primary_yn is True  # updated on second call
