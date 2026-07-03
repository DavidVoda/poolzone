from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.main import app
from app.models import PricingRule, Product, Supplier
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
