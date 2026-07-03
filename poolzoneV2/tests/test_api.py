from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.main import app
from app.models import (
    Category,
    PricingRule,
    Product,
    ProductCategory,
    ProductImage,
    ProductParam,
    Supplier,
    SupplierCategoryMap,
)
from app.sync import suppliers


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded(db_session):
    db_session.add(PricingRule(scope="default", match_value=None, margin_pct=Decimal("0.35")))
    s = Supplier(code="pooltechnika", name="P", feed_url="http://x")
    db_session.add(s)
    db_session.flush()
    p = Product(
        code="ESPA1",
        supplier_id=s.id,
        title="Těsnění",
        price_purchase=Decimal("77.00"),
        margin_pct=Decimal("0.35"),
        coefficient=Decimal("1.0"),
        active=True,
    )
    db_session.add(p)
    db_session.flush()
    return p


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_list_products_computes_sale_price(client, seeded):
    body = client.get("/api/products").json()
    rows = body["items"]
    assert body["total"] == 1
    assert rows[0]["code"] == "ESPA1"
    assert rows[0]["sale_price"] == "118.46"  # 77 / 0.65


def test_search_products(client, seeded):
    assert client.get("/api/products?q=ESPA").json()["total"] == 1
    assert client.get("/api/products?q=nope").json()["total"] == 0


def test_list_products_envelope_and_filters(client, seeded, db_session):
    db_session.add(
        Product(code="AK1", title="Sonda", price_purchase=Decimal("100"), stock=0, active=False)
    )
    db_session.flush()

    body = client.get("/api/products").json()
    assert body["total"] == 2 and len(body["items"]) == 2

    body = client.get("/api/products?filter=active:eq:true").json()
    assert body["total"] == 1 and body["items"][0]["code"] == "ESPA1"

    body = client.get("/api/products?filter=stock:gt:0").json()
    assert body["total"] == 0  # ESPA1 has stock None, AK1 has 0

    body = client.get("/api/products?filter=title:contains:sond").json()
    assert body["total"] == 1 and body["items"][0]["code"] == "AK1"

    body = client.get("/api/products?filter=margin_pct:empty:").json()
    assert body["total"] == 1 and body["items"][0]["code"] == "AK1"

    assert client.get("/api/products?filter=nope:eq:1").status_code == 422
    assert client.get("/api/products?filter=stock:gt:abc").status_code == 422


def test_list_products_sort(client, seeded, db_session):
    db_session.add(Product(code="AK1", title="Sonda"))
    db_session.flush()
    body = client.get("/api/products?sort=-code").json()
    assert [p["code"] for p in body["items"]] == ["ESPA1", "AK1"]
    assert client.get("/api/products?sort=nope").status_code == 422


def test_list_products_overrides_flag(client, seeded, db_session):
    # seeded has explicit margin -> is an override; add a plain product
    db_session.add(Product(code="PLAIN1", title="x"))
    db_session.flush()
    body = client.get("/api/products?overrides=true").json()
    assert [p["code"] for p in body["items"]] == ["ESPA1"]


def test_update_product_owner_fields(client, seeded):
    r = client.patch(f"/api/products/{seeded.id}", json={"title": "EDITED", "coefficient": "0.9"})
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "EDITED"
    assert body["coefficient"] == "0.9000"


def test_update_missing_product_404(client, seeded):
    assert client.patch("/api/products/9999", json={"title": "x"}).status_code == 404


def test_pricing_rules_list_and_update(client, seeded):
    rules = client.get("/api/pricing/rules").json()
    assert rules[0]["margin_pct"] == "0.3500"
    rid = rules[0]["id"]
    r = client.put(f"/api/pricing/rules/{rid}", json={"margin_pct": "0.40"})
    assert r.json()["margin_pct"] == "0.4000"


def test_trigger_export_records_job(client, seeded, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "feeds").mkdir()
    stats = client.post("/api/jobs/export").json()
    assert stats["products"] == 1
    kinds = {j["kind"] for j in client.get("/api/jobs").json()}
    assert "export" in kinds


def test_trigger_sync_uses_adapter(client, seeded, monkeypatch):
    sample = b"<SHOP><SHOPITEM><ITEM_ID>NEW1</ITEM_ID><PRODUCTNAME>New</PRODUCTNAME><PRICE_VAT>121,00</PRICE_VAT></SHOPITEM></SHOP>"
    monkeypatch.setattr(suppliers.pooltechnika, "fetch", lambda url: sample)
    stats = client.post("/api/jobs/sync/pooltechnika").json()
    assert stats["created"] == 1
    assert client.get("/api/products?q=NEW1").json()["total"] == 1


def test_trigger_sync_unknown_supplier_404(client, seeded):
    assert client.post("/api/jobs/sync/nope").status_code == 404


def test_update_product_content_fields(client, seeded):
    r = client.patch(
        f"/api/products/{seeded.id}",
        json={"short_description": "krátký", "seo_title": "SEO", "seo_description": "popis"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["short_description"] == "krátký"
    assert body["seo_title"] == "SEO"
    assert body["seo_description"] == "popis"


def test_product_detail_children_roundtrip(client, seeded, db_session):
    cat = Category(name="Čerpadla")
    db_session.add(cat)
    db_session.flush()
    seeded.params = [ProductParam(name="Výkon", value="8 m3/h", ord=0)]
    seeded.images = [ProductImage(url="http://img/1.jpg", alt=None, ord=0)]
    db_session.add(ProductCategory(product_id=seeded.id, category_id=cat.id, primary_yn=True))
    db_session.flush()

    body = client.get(f"/api/products/{seeded.id}").json()
    assert body["params"] == [{"name": "Výkon", "value": "8 m3/h", "ord": 0}]
    assert body["images"] == [{"url": "http://img/1.jpg", "alt": None, "ord": 0}]
    assert body["categories"] == [{"category_id": cat.id, "primary_yn": True}]

    r = client.patch(
        f"/api/products/{seeded.id}",
        json={
            "params": [
                {"name": "Výkon", "value": "11 m3/h", "ord": 0},
                {"name": "Napětí", "value": "230 V", "ord": 1},
            ],
            "images": [],
            "categories": [{"category_id": cat.id, "primary_yn": False}],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert [p["value"] for p in body["params"]] == ["11 m3/h", "230 V"]
    assert body["images"] == []
    assert body["categories"] == [{"category_id": cat.id, "primary_yn": False}]


def test_list_suppliers(client, seeded):
    rows = client.get("/api/suppliers").json()
    assert rows[0]["code"] == "pooltechnika" and rows[0]["name"] == "P"


def test_categories_crud_and_mappings(client, seeded, db_session):
    root = client.post("/api/categories", json={"name": "Technologie", "parent_id": None}).json()
    child = client.post("/api/categories", json={"name": "Čerpadla", "parent_id": root["id"]}).json()
    assert child["parent_id"] == root["id"]

    r = client.patch(f"/api/categories/{child['id']}", json={"seo_title": "Čerpadla | Poolzone"})
    assert r.json()["seo_title"] == "Čerpadla | Poolzone"

    # root has a child -> delete refused
    assert client.delete(f"/api/categories/{root['id']}").status_code == 409

    names = [c["name"] for c in client.get("/api/categories").json()]
    assert names == ["Technologie", "Čerpadla"]

    m = SupplierCategoryMap(
        supplier_id=seeded.supplier_id, supplier_path="Bazény > Čerpadla", category_id=child["id"]
    )
    db_session.add(m)
    db_session.flush()
    rows = client.get(f"/api/categories/mappings?category_id={child['id']}").json()
    assert rows[0]["supplier_path"] == "Bazény > Čerpadla"

    r = client.patch(f"/api/categories/mappings/{m.id}", json={"category_id": root["id"]})
    assert r.json()["category_id"] == root["id"]

    # child now unreferenced -> delete OK
    assert client.delete(f"/api/categories/{child['id']}").status_code == 200


def test_repull_returns_feed_values(client, seeded, monkeypatch):
    sample = (
        b"<SHOP><SHOPITEM><ITEM_ID>ESPA1</ITEM_ID><PRODUCTNAME>Novy nazev</PRODUCTNAME>"
        b"<PRICE_VAT>121,00</PRICE_VAT></SHOPITEM></SHOP>"
    )
    monkeypatch.setattr(suppliers.pooltechnika, "fetch", lambda url: sample)
    body = client.post(f"/api/products/{seeded.id}/repull").json()
    assert body["title"] == "Novy nazev"
    assert "price_purchase" in body and "params" in body and "image_urls" in body


def test_repull_product_not_in_feed_404(client, seeded, monkeypatch):
    monkeypatch.setattr(suppliers.pooltechnika, "fetch", lambda url: b"<SHOP></SHOP>")
    assert client.post(f"/api/products/{seeded.id}/repull").status_code == 404


def test_ne_filter_keeps_null_rows(client, seeded, db_session):
    db_session.add(Product(code="NOMAN", title="x", manufacturer=None))
    db_session.add(Product(code="BOSCH1", title="y", manufacturer="Bosch"))
    db_session.flush()
    # "not Bosch" must include the NULL-manufacturer row
    codes = {p["code"] for p in client.get("/api/products?filter=manufacturer:ne:Bosch").json()["items"]}
    assert "NOMAN" in codes and "BOSCH1" not in codes


def test_contains_on_numeric_column_422(client, seeded):
    assert client.get("/api/products?filter=stock:contains:5").status_code == 422


def test_update_product_dedups_categories(client, seeded, db_session):
    cat = Category(name="C")
    db_session.add(cat)
    db_session.flush()
    r = client.patch(
        f"/api/products/{seeded.id}",
        json={"categories": [{"category_id": cat.id, "primary_yn": True}, {"category_id": cat.id, "primary_yn": False}]},
    )
    assert r.status_code == 200
    assert r.json()["categories"] == [{"category_id": cat.id, "primary_yn": True}]


def test_repull_no_feed_url_409(client, seeded, db_session):
    db_session.execute(
        Supplier.__table__.update().where(Supplier.id == seeded.supplier_id).values(feed_url=None)
    )
    db_session.flush()
    assert client.post(f"/api/products/{seeded.id}/repull").status_code == 409


def test_category_cycle_rejected(client, seeded):
    root = client.post("/api/categories", json={"name": "R", "parent_id": None}).json()
    child = client.post("/api/categories", json={"name": "C", "parent_id": root["id"]}).json()
    # making root a child of its own child -> cycle -> 409
    assert client.patch(f"/api/categories/{root['id']}", json={"parent_id": child["id"]}).status_code == 409
