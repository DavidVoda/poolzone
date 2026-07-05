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
    monkeypatch.setattr(runner, "_claude", lambda *a, **k: "# Plan\nstep 1")
    monkeypatch.setattr(runner, "session_scope", _scope(db_session))
    runner.run_plan(rid)
    db_session.expire_all()
    r = db_session.get(FeatureRequest, rid)
    assert r.status == "planned"
    assert r.plan.startswith("# Plan")


def test_run_plan_failure_returns_to_draft(db_session, monkeypatch):
    rid = _req(db_session)

    def boom(*a, **k):
        raise RuntimeError("claude down")

    monkeypatch.setattr(runner, "_claude", boom)
    monkeypatch.setattr(runner, "session_scope", _scope(db_session))
    runner.run_plan(rid)
    db_session.expire_all()
    r = db_session.get(FeatureRequest, rid)
    assert r.status == "draft"
    assert "claude down" in r.error


def test_run_implement_builds_compare_url(db_session, monkeypatch):
    rid = _req(db_session, status="implementing", plan="do the thing")
    monkeypatch.setattr(runner, "_claude", lambda *a, **k: "committed and pushed")
    monkeypatch.setattr(runner, "_git", lambda *a: None)
    monkeypatch.setattr(
        runner, "_compare_url", lambda b: f"https://github.com/o/r/compare/{b}?expand=1"
    )
    monkeypatch.setattr(runner, "session_scope", _scope(db_session))
    runner.run_implement(rid)
    db_session.expire_all()
    r = db_session.get(FeatureRequest, rid)
    assert r.status == "done"
    assert r.branch == f"feat/req-{rid}"
    assert r.pr_url == f"https://github.com/o/r/compare/feat/req-{rid}?expand=1"


def test_compare_url_from_ssh_remote(monkeypatch):
    import subprocess

    class R:
        returncode = 0
        stdout = "git@github.com:acme/poolzone.git\n"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: R())
    assert (
        runner._compare_url("feat/x") == "https://github.com/acme/poolzone/compare/feat/x?expand=1"
    )
