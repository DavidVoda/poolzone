import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.main import app


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def _create(client, **kw):
    return client.post(
        "/api/feature-requests", json={"title": "t", "description": "d", **kw}
    ).json()


def _to(client, rid, to, **body):
    return client.post(f"/api/feature-requests/{rid}/transition", json={"to": to, **body})


def test_create_list_get_patch(client):
    rid = _create(client, tag="ui", priority="high")["id"]
    assert any(r["id"] == rid for r in client.get("/api/feature-requests").json())
    got = client.get(f"/api/feature-requests/{rid}").json()
    assert got["tag"] == "ui" and got["status"] == "draft"
    assert (
        client.patch(f"/api/feature-requests/{rid}", json={"plan": "# p"}).json()["plan"] == "# p"
    )


def test_illegal_transition_409(client):
    rid = _create(client)["id"]
    assert _to(client, rid, "planned").status_code == 409  # draft can't jump to planned


def test_happy_path(client):
    rid = _create(client)["id"]
    assert _to(client, rid, "ready_for_plan").json()["status"] == "ready_for_plan"
    assert _to(client, rid, "planning").json()["status"] == "planning"
    # planning -> planned needs a plan
    assert _to(client, rid, "planned").status_code == 422
    r = _to(client, rid, "planned", plan="# Plan").json()
    assert r["status"] == "planned" and r["plan"] == "# Plan"
    assert _to(client, rid, "ready_for_impl").json()["status"] == "ready_for_impl"
    assert _to(client, rid, "implementing").json()["status"] == "implementing"
    r = _to(client, rid, "implemented", execution_log="edited GlobalSearch.tsx").json()
    assert r["status"] == "implemented" and r["execution_log"] == "edited GlobalSearch.tsx"


def test_replan_reset(client):
    rid = _create(client)["id"]
    _to(client, rid, "ready_for_plan")
    _to(client, rid, "planning")
    _to(client, rid, "planned", plan="p")
    # operator sends it back to draft with a note for the re-plan
    r = _to(client, rid, "draft", review_note="use pricing helper").json()
    assert r["status"] == "draft" and r["review_note"] == "use pricing helper"


def test_error_set_and_cleared(client):
    rid = _create(client)["id"]
    _to(client, rid, "ready_for_plan")
    _to(client, rid, "planning")
    # agent failed -> back to ready_for_plan with an error
    r = _to(client, rid, "ready_for_plan", error="boom").json()
    assert r["error"] == "boom"
    # next successful claim clears it
    assert _to(client, rid, "planning").json()["error"] is None
