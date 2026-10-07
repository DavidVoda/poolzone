import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.main import app
from app.auth import hash_password, verify_password
from app.models import User


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed(db, email="admin@x.cz", role="admin", pw="secret123"):
    u = User(email=email, name=email.split("@")[0], role=role, password_hash=hash_password(pw))
    db.add(u)
    db.flush()
    return u


def test_password_hash_roundtrip():
    h = hash_password("hunter2")
    assert h != "hunter2"
    assert verify_password("hunter2", h)
    assert not verify_password("wrong", h)
    # Any length works (sha256 pre-hash dodges bcrypt's 72-byte cap).
    long = "p" * 200
    assert verify_password(long, hash_password(long))


def test_login_rejects_bad_credentials(client, db_session):
    _seed(db_session)
    assert client.post("/api/auth/login", json={"email": "admin@x.cz", "password": "nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "ghost@x.cz", "password": "x"}).status_code == 401


def test_login_me_logout_flow(client, db_session):
    _seed(db_session)
    # dev: not logged in -> auth_required False, no user
    me = client.get("/api/auth/me").json()
    assert me == {"auth_required": False, "user": None}

    r = client.post("/api/auth/login", json={"email": "admin@x.cz", "password": "secret123"})
    assert r.status_code == 200
    assert r.json()["email"] == "admin@x.cz"

    me = client.get("/api/auth/me").json()
    assert me["user"]["email"] == "admin@x.cz"

    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").json()["user"] is None


def test_inactive_user_cannot_login(client, db_session):
    u = _seed(db_session)
    u.active = False
    db_session.flush()
    assert client.post("/api/auth/login", json={"email": "admin@x.cz", "password": "secret123"}).status_code == 401


def test_user_crud(client, db_session):
    _seed(db_session)
    r = client.post(
        "/api/users",
        json={"email": "eva@x.cz", "name": "Eva", "password": "pw12345", "role": "member"},
    )
    assert r.status_code == 201
    uid = r.json()["id"]

    assert any(u["email"] == "eva@x.cz" for u in client.get("/api/users").json())

    # duplicate email rejected
    assert client.post(
        "/api/users", json={"email": "eva@x.cz", "name": "x", "password": "y", "role": "member"}
    ).status_code == 409

    # promote + rename
    r = client.patch(f"/api/users/{uid}", json={"role": "admin", "name": "Eva P"})
    assert r.json()["role"] == "admin" and r.json()["name"] == "Eva P"

    # password reset then login works
    assert client.post(f"/api/users/{uid}/password", json={"password": "newpass1"}).status_code == 204
    assert client.post("/api/auth/login", json={"email": "eva@x.cz", "password": "newpass1"}).status_code == 200

    assert client.delete(f"/api/users/{uid}").status_code == 204


def test_cannot_remove_last_admin(client, db_session):
    admin = _seed(db_session)  # the only admin
    # demote
    assert client.patch(f"/api/users/{admin.id}", json={"role": "member"}).status_code == 409
    # deactivate
    assert client.patch(f"/api/users/{admin.id}", json={"active": False}).status_code == 409
    # delete
    assert client.delete(f"/api/users/{admin.id}").status_code == 409


def test_production_gate_blocks_anonymous(client, db_session, monkeypatch):
    _seed(db_session)
    monkeypatch.setattr("app.auth.IS_PRODUCTION", True)
    # anonymous hit on a guarded route -> 401
    assert client.get("/api/products").status_code == 401
    # after login the same route is reachable
    assert client.post("/api/auth/login", json={"email": "admin@x.cz", "password": "secret123"}).status_code == 200
    assert client.get("/api/products").status_code == 200
