# Feature Request Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Operator requests app changes from the admin UI; an AI agent (headless `claude`) plans, operator reviews, agent implements in an isolated worktree + PR. Requests shown as a filterable card list with detail.

**Architecture:** New `FeatureRequest` table + REST router mirroring `jobs.py`. An agent bridge (`app/agent/runner.py`) shells `claude -p`, guarded by a one-at-a-time lock, run via FastAPI `BackgroundTasks`. Implement runs in a `git worktree` so the live tree is never touched. A committed skill file holds the plan/implement procedure. React card page with client-side filter/sort.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, React 19 + TanStack Query, shadcn/ui.

**Ponytail deviations from spec (deliberate, simpler):**
- List filter/sort is **client-side** in React (requests are few); backend GET just orders by `updated_at desc` with an optional `status` query param. Skips wiring `filters.py` for the new table — add server-side filtering only if request volume ever grows.
- No separate implementer subagent — the one skill file covers plan + implement.

---

### Task 1: `FeatureRequest` model + migration

**Files:** Modify `poolzoneV2/app/models.py`; Create `poolzoneV2/app/migrations/versions/b2c3d4e5f6a7_feature_requests.py`

- [ ] **Step 1:** Append model to `models.py` (after `JobRun`):

```python
class FeatureRequest(Base):
    __tablename__ = "feature_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)  # operator user story
    priority: Mapped[str] = mapped_column(String(16), default="normal")  # low|normal|high
    tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # draft|planning|planned|approved|implementing|done|failed
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    branch: Mapped[str | None] = mapped_column(String(200), nullable=True)
    pr_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 2:** Create the migration (chain `down_revision = "a1b2c3d4e5f6"`), `create_table` with the columns above + index on `status`. `downgrade` drops the table.

- [ ] **Step 3:** Apply: `./.venv/bin/alembic upgrade head`. Expected: no error.

- [ ] **Step 4:** Commit `feat(v2): feature_requests table`.

### Task 2: Agent bridge — `app/agent/runner.py`

**Files:** Create `poolzoneV2/app/agent/__init__.py`, `poolzoneV2/app/agent/runner.py`; Create `poolzoneV2/tests/test_agent_runner.py`

- [ ] **Step 1:** Write `runner.py`:

```python
from __future__ import annotations

import re
import subprocess
import threading
from pathlib import Path

from app.db import session_scope
from app.models import FeatureRequest

REPO = Path(__file__).resolve().parents[3]  # git root (poolzone/)
SKILL = ".claude/skills/feature-pipeline/SKILL.md"
_TIMEOUT = 1800  # 30 min per claude run

# ponytail: one agent run at a time — single-process app, an in-memory lock is
# enough. Move to a DB flag / queue only if multiple workers ever run.
_lock = threading.Lock()


class Busy(Exception):
    """An agent run is already in progress."""


def is_busy() -> bool:
    return _lock.locked()


def _claude(prompt: str, cwd: Path) -> str:
    r = subprocess.run(
        ["claude", "-p", prompt],
        cwd=cwd, capture_output=True, text=True, timeout=_TIMEOUT,
    )
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[:2000] or "claude failed")
    return r.stdout.strip()


def _git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True)


def _plan_prompt(req: FeatureRequest) -> str:
    note = f"\n\nA previous plan was rejected. Operator note:\n{req.review_note}" if req.review_note else ""
    return (
        f"Read {SKILL} and follow its PLANNING section for this repo.\n\n"
        f"User story (title: {req.title}):\n{req.description}{note}\n\n"
        "Output ONLY the implementation plan as markdown. Write no code, change no files."
    )


def _impl_prompt(plan: str) -> str:
    return (
        f"Read {SKILL} and follow its IMPLEMENTING section.\n\n"
        f"Implement this plan:\n\n{plan}\n\n"
        "Print the opened PR URL as the last line of your output."
    )


def _set(req_id: int, **fields) -> None:
    with session_scope() as db:
        req = db.get(FeatureRequest, req_id)
        for k, v in fields.items():
            setattr(req, k, v)


def run_plan(req_id: int) -> None:
    if not _lock.acquire(blocking=False):
        _set(req_id, status="draft", error="agent busy")
        return
    try:
        with session_scope() as db:
            prompt = _plan_prompt(db.get(FeatureRequest, req_id))
        out = _claude(prompt, REPO)
        _set(req_id, plan=out, status="planned", error=None, review_note=None)
    except Exception as e:  # noqa: BLE001 - surface any failure to the operator
        _set(req_id, status="draft", error=str(e)[:2000])
    finally:
        _lock.release()


def run_implement(req_id: int) -> None:
    if not _lock.acquire(blocking=False):
        _set(req_id, status="approved", error="agent busy")
        return
    branch = f"feat/req-{req_id}"
    tree = REPO.parent / f"pz-req-{req_id}"
    try:
        with session_scope() as db:
            plan = db.get(FeatureRequest, req_id).plan or ""
        _git("worktree", "add", str(tree), "-b", branch)
        try:
            out = _claude(_impl_prompt(plan), tree)
        finally:
            _git("worktree", "remove", "--force", str(tree))
        m = re.search(r"https://\S+/pull/\d+", out)
        _set(req_id, execution_log=out, branch=branch,
             pr_url=(m.group(0) if m else None), status="done", error=None)
    except Exception as e:  # noqa: BLE001
        _set(req_id, status="failed", error=str(e)[:2000])
    finally:
        _lock.release()
```

- [ ] **Step 2:** Test (`test_agent_runner.py`) — mock `_claude`, assert transitions and PR-url parse. No real claude/git:

```python
from app.agent import runner
from app.models import FeatureRequest


def _req(db, **kw):
    r = FeatureRequest(title="t", description="d", status="planning", **kw)
    db.add(r); db.flush(); db.commit()
    return r.id


def test_run_plan_success(db_session, monkeypatch):
    rid = _req(db_session)
    monkeypatch.setattr(runner, "_claude", lambda p, c: "# Plan\nstep 1")
    monkeypatch.setattr(runner, "session_scope", _scope(db_session))
    runner.run_plan(rid)
    db_session.expire_all()
    r = db_session.get(FeatureRequest, rid)
    assert r.status == "planned" and r.plan.startswith("# Plan")


def test_run_plan_failure_returns_to_draft(db_session, monkeypatch):
    rid = _req(db_session)
    def boom(p, c): raise RuntimeError("claude down")
    monkeypatch.setattr(runner, "_claude", boom)
    monkeypatch.setattr(runner, "session_scope", _scope(db_session))
    runner.run_plan(rid)
    db_session.expire_all()
    assert db_session.get(FeatureRequest, rid).status == "draft"
```

Helper `_scope` wraps the test session as a no-commit contextmanager (define at top of file):

```python
from contextlib import contextmanager

def _scope(session):
    @contextmanager
    def scope():
        yield session
        session.flush()
    return scope
```

- [ ] **Step 3:** Run: `./.venv/bin/pytest tests/test_agent_runner.py -v`. Expected PASS.

- [ ] **Step 4:** Commit `feat(v2): agent runner bridge (claude -p, worktree, lock)`.

### Task 3: Skill file

**Files:** Create `.claude/skills/feature-pipeline/SKILL.md` (repo root)

- [ ] **Step 1:** Write the skill with YAML frontmatter (`name`, `description`) and two sections — **PLANNING** (read `poolzoneV2/CLAUDE.md` + README, respect invariants: dual pricing formula, `npm run api:types`, Alembic migration for column changes, whitelist import semantics; output markdown, no code) and **IMPLEMENTING** (work in cwd which is already the worktree; run backend `pytest` + `npm run build`/`lint`; ruff format; commit; `git push -u origin <branch>`; `gh pr create --fill`; print PR URL last; if a step's tool is missing, stop and report it clearly).

- [ ] **Step 2:** Commit `feat: feature-pipeline skill (plan + implement procedure)`.

### Task 4: Schemas + router

**Files:** Modify `poolzoneV2/app/api/schemas.py`, `poolzoneV2/app/api/main.py`; Create `poolzoneV2/app/api/routers/feature_requests.py`

- [ ] **Step 1:** Add to `schemas.py`:

```python
class FeatureRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    priority: str
    tag: str | None
    status: str
    plan: str | None
    review_note: str | None
    execution_log: str | None
    branch: str | None
    pr_url: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class FeatureRequestCreate(BaseModel):
    title: str
    description: str
    priority: str = "normal"
    tag: str | None = None


class FeatureRequestPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    tag: str | None = None
    plan: str | None = None


class ReviewNote(BaseModel):
    review_note: str
```

- [ ] **Step 2:** Write `routers/feature_requests.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent import runner
from app.api.deps import get_db
from app.api.schemas import (
    FeatureRequestCreate,
    FeatureRequestOut,
    FeatureRequestPatch,
    ReviewNote,
)
from app.models import FeatureRequest

router = APIRouter(prefix="/api/feature-requests", tags=["feature-requests"])


def _get(db: Session, req_id: int) -> FeatureRequest:
    req = db.get(FeatureRequest, req_id)
    if req is None:
        raise HTTPException(404, "feature request not found")
    return req


def _require(req: FeatureRequest, *allowed: str) -> None:
    if req.status not in allowed:
        raise HTTPException(409, f"action not allowed in status '{req.status}'")


@router.get("", response_model=list[FeatureRequestOut])
def list_requests(db: Session = Depends(get_db), status: str | None = None):
    stmt = select(FeatureRequest).order_by(FeatureRequest.updated_at.desc())
    if status:
        stmt = stmt.where(FeatureRequest.status == status)
    return list(db.execute(stmt).scalars())


@router.post("", response_model=FeatureRequestOut, status_code=201)
def create_request(body: FeatureRequestCreate, db: Session = Depends(get_db)):
    req = FeatureRequest(**body.model_dump())
    db.add(req)
    db.flush()
    return req


@router.get("/{req_id}", response_model=FeatureRequestOut)
def get_request(req_id: int, db: Session = Depends(get_db)):
    return _get(db, req_id)


@router.patch("/{req_id}", response_model=FeatureRequestOut)
def patch_request(req_id: int, body: FeatureRequestPatch, db: Session = Depends(get_db)):
    req = _get(db, req_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(req, k, v)
    return req


@router.post("/{req_id}/plan", response_model=FeatureRequestOut)
def plan(req_id: int, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    req = _get(db, req_id)
    _require(req, "draft")
    if runner.is_busy():
        raise HTTPException(409, "agent busy")
    req.status = "planning"
    req.error = None
    tasks.add_task(runner.run_plan, req.id)
    return req


@router.post("/{req_id}/approve", response_model=FeatureRequestOut)
def approve(req_id: int, db: Session = Depends(get_db)):
    req = _get(db, req_id)
    _require(req, "planned")
    req.status = "approved"
    return req


@router.post("/{req_id}/reject", response_model=FeatureRequestOut)
def reject(req_id: int, body: ReviewNote, db: Session = Depends(get_db)):
    req = _get(db, req_id)
    _require(req, "planned")
    req.status = "draft"
    req.review_note = body.review_note
    return req


@router.post("/{req_id}/implement", response_model=FeatureRequestOut)
def implement(req_id: int, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    req = _get(db, req_id)
    _require(req, "approved", "failed")
    if runner.is_busy():
        raise HTTPException(409, "agent busy")
    req.status = "implementing"
    req.error = None
    tasks.add_task(runner.run_implement, req.id)
    return req
```

- [ ] **Step 3:** Register in `main.py`: import `feature_requests` and `app.include_router(feature_requests.router)`.

- [ ] **Step 4:** Test (`tests/test_feature_requests_api.py`) — mock `runner.run_plan`/`run_implement` so background tasks don't spawn claude; assert create/list/get/patch + each transition + 409 on bad status. Example:

```python
def test_plan_transition(client, monkeypatch):
    import app.api.routers.feature_requests as r
    monkeypatch.setattr(r.runner, "is_busy", lambda: False)
    called = {}
    monkeypatch.setattr(r.runner, "run_plan", lambda rid: called.setdefault("id", rid))
    rid = client.post("/api/feature-requests", json={"title": "t", "description": "d"}).json()["id"]
    resp = client.post(f"/api/feature-requests/{rid}/plan")
    assert resp.status_code == 200 and resp.json()["status"] == "planning"
    assert called["id"] == rid


def test_approve_requires_planned(client):
    rid = client.post("/api/feature-requests", json={"title": "t", "description": "d"}).json()["id"]
    assert client.post(f"/api/feature-requests/{rid}/approve").status_code == 409
```

- [ ] **Step 5:** Run: `./.venv/bin/pytest tests/test_feature_requests_api.py -v`. Expected PASS.

- [ ] **Step 6:** Regenerate types: `cd frontend && npm run api:types`.

- [ ] **Step 7:** Commit `feat(v2): feature-requests API + schemas`.

### Task 5: Frontend page

**Files:** Create `poolzoneV2/frontend/src/pages/FeatureRequests.tsx`; Modify `App.tsx`, `AppShell.tsx`, `StatusBadge.tsx`; add `FeatureRequest` alias to `lib/api.ts`

- [ ] **Step 1:** Add status styles/labels to `StatusBadge.tsx` `STYLES`/`LABELS`: `draft`(slate,"koncept"), `planning`(sky,"plánuji"), `planned`(indigo,"naplánováno"), `approved`(amber,"schváleno"), `implementing`(sky,"realizuji"), `done`(green,"hotovo"), `failed`(red,"chyba").

- [ ] **Step 2:** Add alias in `lib/api.ts`:
```ts
export type FeatureRequest = paths["/api/feature-requests"]["get"]["responses"]["200"]["content"]["application/json"][number]
```

- [ ] **Step 3:** Write `FeatureRequests.tsx`: PageHeader + "Nový požadavek" dialog (title/description/priority/tag → POST). Card grid (`grid gap-3 sm:grid-cols-2 lg:grid-cols-3`) with StatusBadge, title, priority + tag chips, truncated description, updated-at. Filter selects (status/priority/tag) + sort toggle, all **client-side** over the fetched list. Card click → Sheet detail: full description, plan (editable `<Textarea>` when `planned`, else rendered as `<pre>`), execution log `<pre>`, PR link, and status-driven buttons wired to the mutations below. `useQuery(["feature-requests"])` with `refetchInterval` = 4 s while any card is `planning`/`implementing`, else off. Mutations POST to `/plan`,`/approve`,`/reject`,`/implement`, PATCH plan on save; `invalidateQueries(["feature-requests"])` + toast on settle.

- [ ] **Step 4:** Route in `App.tsx`: `{ path: "/feature-requests", element: <FeatureRequests /> }` + import.

- [ ] **Step 5:** Nav in `AppShell.tsx` `NAV`: `{ to: "/feature-requests", label: "Požadavky", icon: Lightbulb }` (import `Lightbulb` from lucide-react); place above the disabled `Návrhy`.

- [ ] **Step 6:** Build check: `cd frontend && npm run build && npm run lint`. Expected: no errors.

- [ ] **Step 7:** Commit `feat(v2): feature-requests admin page`.

### Task 6: Docs + verify

**Files:** Modify `poolzoneV2/CLAUDE.md`

- [ ] **Step 1:** Add a line to CLAUDE.md Layout: `app/agent/` — headless-claude bridge for the feature-request pipeline (plan/implement, worktree-isolated, one-at-a-time lock). Note the `gh` + `claude` host prerequisite and that the page must stay localhost/trusted-operator only.

- [ ] **Step 2:** Full backend suite: `./.venv/bin/pytest`. Expected PASS.

- [ ] **Step 3:** Commit `docs(v2): note agent pipeline in CLAUDE.md`.

---

## Self-review notes
- Spec coverage: table (T1), agent bridge+worktree+lock (T2), skill (T3), API all endpoints+409 (T4), FE cards/filter/sort/detail/poll (T5), tests mocked (T2,T4), constraints doc (T6). Covered.
- Deviation: client-side filter/sort + optional `status` param instead of `filters.py` reuse — noted at top.
- `gh` absent on host: implement will land in `failed` with the error surfaced; operator installs `gh` + authenticates to enable PRs.
