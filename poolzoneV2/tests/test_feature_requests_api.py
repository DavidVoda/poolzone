import pytest
from fastapi.testclient import TestClient

import app.api.routers.feature_requests as fr
from app.api.deps import get_db
from app.api.main import app


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def _create(client, **kw):
    body = {"title": "t", "description": "d", **kw}
    return client.post("/api/feature-requests", json=body).json()


def test_create_list_get_patch(client):
    rid = _create(client, tag="ui", priority="high")["id"]

    lst = client.get("/api/feature-requests").json()
    assert any(r["id"] == rid for r in lst)

    got = client.get(f"/api/feature-requests/{rid}").json()
    assert got["tag"] == "ui" and got["status"] == "draft"

    patched = client.patch(f"/api/feature-requests/{rid}", json={"plan": "# p"}).json()
    assert patched["plan"] == "# p"


def test_plan_transition_schedules_runner(client, monkeypatch):
    monkeypatch.setattr(fr.runner, "is_busy", lambda: False)
    called = {}
    monkeypatch.setattr(fr.runner, "run_plan", lambda rid: called.setdefault("id", rid))
    rid = _create(client)["id"]
    resp = client.post(f"/api/feature-requests/{rid}/plan")
    assert resp.status_code == 200
    assert resp.json()["status"] == "planning"
    assert called["id"] == rid


def test_plan_409_when_busy(client, monkeypatch):
    monkeypatch.setattr(fr.runner, "is_busy", lambda: True)
    rid = _create(client)["id"]
    assert client.post(f"/api/feature-requests/{rid}/plan").status_code == 409


def test_approve_requires_planned(client):
    rid = _create(client)["id"]
    assert client.post(f"/api/feature-requests/{rid}/approve").status_code == 409


def test_reject_needs_note_and_returns_to_draft(client, monkeypatch, db_session):
    from app.models import FeatureRequest

    rid = _create(client)["id"]
    db_session.get(FeatureRequest, rid).status = "planned"
    db_session.flush()

    # missing note -> 422
    assert client.post(f"/api/feature-requests/{rid}/reject", json={}).status_code == 422

    resp = client.post(f"/api/feature-requests/{rid}/reject", json={"review_note": "redo pricing"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"
    assert resp.json()["review_note"] == "redo pricing"


def test_implement_requires_approved_or_failed(client, monkeypatch, db_session):
    from app.models import FeatureRequest

    monkeypatch.setattr(fr.runner, "is_busy", lambda: False)
    monkeypatch.setattr(fr.runner, "run_implement", lambda rid: None)
    rid = _create(client)["id"]
    # draft -> 409
    assert client.post(f"/api/feature-requests/{rid}/implement").status_code == 409

    db_session.get(FeatureRequest, rid).status = "approved"
    db_session.flush()
    resp = client.post(f"/api/feature-requests/{rid}/implement")
    assert resp.status_code == 200 and resp.json()["status"] == "implementing"
