from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import JobRun


class JobBusyError(Exception):
    """Another job is already running — refuse to start a second one."""


def assert_idle(session: Session) -> None:
    """Raise JobBusyError if any job is currently running. Cheap guard for endpoints."""
    if session.execute(select(JobRun.id).where(JobRun.status == "running")).first():
        raise JobBusyError()


@contextmanager
def job_run(session: Session, kind: str):
    """Record a JobRun and **commit it as 'running' up front** so it is visible to other
    requests (the Jobs tab) and blocks concurrent starts. On exit, marks success (unless
    the body set another status, e.g. 'skipped') or 'failed', and commits.

    Jobs run synchronously, so without the up-front commit the running row stays inside an
    open transaction and no other request can see it — which is why running jobs never
    showed and nothing stopped a second one from starting.
    """
    assert_idle(session)
    job = JobRun(kind=kind, status="running", stats={})
    session.add(job)
    session.commit()  # visible + acts as the lock
    try:
        yield job
        if job.status == "running":
            job.status = "success"
        job.finished_at = datetime.now(timezone.utc)
        session.commit()
    except Exception:
        job.status = "failed"
        job.finished_at = datetime.now(timezone.utc)
        session.commit()
        raise
