from contextlib import contextmanager

from app.agent import runner
from app.models import FeatureRequest


def _scope(session):
    @contextmanager
    def scope():
        yield session
        session.flush()

    return scope


def _req(db, **kw):
    kw.setdefault("status", "planning")
    r = FeatureRequest(title="t", description="d", **kw)
    db.add(r)
    db.flush()
    return r.id


def test_run_plan_success(db_session, monkeypatch):
    rid = _req(db_session)
    monkeypatch.setattr(runner, "_claude", lambda p, c: "# Plan\nstep 1")
    monkeypatch.setattr(runner, "session_scope", _scope(db_session))
    runner.run_plan(rid)
    db_session.expire_all()
    r = db_session.get(FeatureRequest, rid)
    assert r.status == "planned"
    assert r.plan.startswith("# Plan")


def test_run_plan_failure_returns_to_draft(db_session, monkeypatch):
    rid = _req(db_session)

    def boom(p, c):
        raise RuntimeError("claude down")

    monkeypatch.setattr(runner, "_claude", boom)
    monkeypatch.setattr(runner, "session_scope", _scope(db_session))
    runner.run_plan(rid)
    db_session.expire_all()
    r = db_session.get(FeatureRequest, rid)
    assert r.status == "draft"
    assert "claude down" in r.error


def test_run_implement_parses_pr_url(db_session, monkeypatch):
    rid = _req(db_session, status="implementing", plan="do the thing")
    monkeypatch.setattr(runner, "_claude", lambda p, c: "done\nhttps://github.com/x/y/pull/42")
    monkeypatch.setattr(runner, "_git", lambda *a: None)
    monkeypatch.setattr(runner, "session_scope", _scope(db_session))
    runner.run_implement(rid)
    db_session.expire_all()
    r = db_session.get(FeatureRequest, rid)
    assert r.status == "done"
    assert r.pr_url == "https://github.com/x/y/pull/42"
    assert r.branch == f"feat/req-{rid}"
