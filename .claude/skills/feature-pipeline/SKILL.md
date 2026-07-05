---
name: feature-pipeline
description: Turn an operator user story into a repo-specific plan, then implement an approved plan in the poolzoneV2 admin app. Invoked headless by the feature-request pipeline (app/agent/runner.py).
---

# Feature Pipeline

You are the agent behind the poolzoneV2 admin app's feature-request pipeline. You
run headless (`claude -p`). The middleware lives in `poolzoneV2/`. The prompt tells
you which section applies.

**Always first:** read `poolzoneV2/CLAUDE.md` and `poolzoneV2/README.md`. Respect
every invariant there. The ones that bite:

- **Pricing formula is duplicated** in `app/pricing.py` and `frontend/src/lib/pricing.ts`
  — change one, change the other, update both test suites.
- **API types are generated** — after any router/schema change run `npm run api:types`
  (from `frontend/`).
- **Schema changes need an Alembic migration** chained to the current head.
- **Whitelist import semantics** — a new row gets every field; an existing row only
  gets whitelisted fields overwritten. Preserve it.
- Backend: **ruff** (line length 100). Frontend lint: **oxlint** (`npm run lint`).
- DB is on host port **5433**. Run backend commands from `poolzoneV2/` with `./.venv/bin/...`.

## PLANNING

Input: an operator user story (and maybe a rejection note to address).

Produce an implementation plan as **markdown only**. **Write no code. Change no files.**
Read whatever source you need to ground the plan in reality, but do not edit.

The plan must contain:
- **Goal** — one sentence.
- **Files** — exact paths to create/modify, one line each on what changes.
- **Steps** — ordered, concrete. Name the functions/columns/components involved.
  Call out any migration, any `api:types` regen, any pricing-formula duplication.
- **Tests** — what to add and where (`tests/test_*.py`, `*.test.ts`).
- **Risks / open questions** — anything the operator should decide.

Keep it lazy (ponytail): reuse existing helpers, prefer the smallest change that
works, no speculative abstractions. Output the plan and nothing else.

## IMPLEMENTING

Input: an approved plan. Your current working directory is **already an isolated git
worktree on a fresh branch** — just work here; do not create branches or worktrees.

1. Implement the plan. Follow existing patterns in the touched files.
2. Honour the invariants above — migration if schema changed, `npm run api:types` if
   the API changed, both pricing files if pricing changed.
3. **Verify before committing:**
   - Backend: `./.venv/bin/pytest` (from `poolzoneV2/`) — must pass.
   - Frontend (if touched): `cd frontend && npm run build && npm run lint` — must pass.
   - `./.venv/bin/ruff format app tests && ./.venv/bin/ruff check app tests`.
4. Commit with a Conventional Commit message describing the change.
5. Push: `git push -u origin <current-branch>`. **Do not open a PR** — the caller
   builds a GitHub compare/PR link from the pushed branch. Plain git only; `gh` is
   not required.

If the push fails (no remote, unauthenticated, DB down, tests red), **stop and report
exactly what failed** — do not fake success. A partial, honest failure is recoverable;
a false "done" is not.
