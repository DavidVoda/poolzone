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
    rows = client.get("/api/products").json()
    assert len(rows) == 1
    assert rows[0]["code"] == "ESPA1"
    assert rows[0]["sale_price"] == "118.46"  # 77 / 0.65


def test_search_products(client, seeded):
    assert len(client.get("/api/products?q=ESPA").json()) == 1
    assert len(client.get("/api/products?q=nope").json()) == 0


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
    assert len(client.get("/api/products?q=NEW1").json()) == 1


def test_trigger_sync_unknown_supplier_404(client, seeded):
    assert client.post("/api/jobs/sync/nope").status_code == 404
