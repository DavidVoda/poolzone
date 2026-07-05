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
LOG_DIR = Path("/tmp/poolzone-agent")  # per-request live logs: tail -f to watch


def log_path(req_id: int, phase: str) -> Path:
    return LOG_DIR / f"req-{req_id}-{phase}.log"


# ponytail: one agent run at a time — single-process app, an in-memory lock is
# enough. Move to a DB flag / queue only if multiple workers ever run.
_lock = threading.Lock()


class Busy(Exception):
    """An agent run is already in progress."""


def is_busy() -> bool:
    return _lock.locked()


def _claude(prompt: str, cwd: Path, out: Path, verbose: bool = False) -> str:
    """Run headless claude, streaming stdout+stderr live to `out` (tail -f to watch)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["claude", "-p", prompt] + (["--verbose"] if verbose else [])
    with out.open("w") as f:
        r = subprocess.run(
            cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, text=True, timeout=_TIMEOUT
        )
    text = out.read_text().strip()
    if r.returncode != 0:
        raise RuntimeError(text[-2000:] or "claude failed")
    return text


def _git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True)


def _compare_url(branch: str) -> str | None:
    """GitHub 'open a PR' URL for a pushed branch, derived from origin. No gh needed."""
    r = subprocess.run(
        ["git", "remote", "get-url", "origin"], cwd=REPO, capture_output=True, text=True
    )
    if r.returncode != 0:
        return None
    m = re.match(r"(?:git@|https://|ssh://git@)([^:/]+)[:/](.+?)(?:\.git)?/?$", r.stdout.strip())
    if not m:
        return None
    return f"https://{m.group(1)}/{m.group(2)}/compare/{branch}?expand=1"


def _plan_prompt(req: FeatureRequest) -> str:
    note = (
        f"\n\nA previous plan was rejected. Operator note:\n{req.review_note}"
        if req.review_note
        else ""
    )
    return (
        f"Read {SKILL} and follow its PLANNING section for this repo.\n\n"
        f"User story (title: {req.title}):\n{req.description}{note}\n\n"
        "Output ONLY the implementation plan as markdown. Write no code, change no files."
    )


def _impl_prompt(plan: str) -> str:
    return (
        f"Read {SKILL} and follow its IMPLEMENTING section.\n\n"
        f"Implement this plan:\n\n{plan}\n\n"
        "Commit and push the branch. Do NOT open a PR — the caller builds the PR link."
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
        out = _claude(prompt, REPO, log_path(req_id, "plan"))
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
            out = _claude(_impl_prompt(plan), tree, log_path(req_id, "implement"), verbose=True)
        finally:
            _git("worktree", "remove", "--force", str(tree))
        _set(
            req_id,
            execution_log=out,
            branch=branch,
            pr_url=_compare_url(branch),
            status="done",
            error=None,
        )
    except Exception as e:  # noqa: BLE001
        _set(req_id, status="failed", error=str(e)[:2000])
    finally:
        _lock.release()
