# Feature Request Pipeline — design

**Date:** 2026-07-05
**Status:** approved, pending implementation plan
**Repo:** `poolzoneV2/`

## Goal

Let a technical operator request app changes from inside the admin UI. A request
flows: operator writes a user-story **draft** → AI agent generates a **plan** →
operator **reviews** (edit / approve / reject) → on approval the agent
**implements** the change in an isolated git worktree and opens a **PR**. Plan and
execution are stored and displayed on a new FE tab as a filterable/sortable list of
cards with a detail view.

The "agent" is Claude Code run headless (`claude -p`) on the backend host,
triggered by FE buttons (human in the loop at every transition). No background
watcher daemon. Local / single-operator use for now.

## Scope

In:
- `FeatureRequest` table + Alembic migration.
- REST API (`app/api/routers/feature_requests.py`) mirroring the `jobs.py` pattern.
- Agent bridge (`app/agent/runner.py`) that shells `claude -p` for plan + implement.
- A skill (`.claude/skills/feature-pipeline/SKILL.md`) holding the plan/implement
  procedure, referenced by the backend prompt.
- FE page (`frontend/src/pages/FeatureRequests.tsx`) + nav + route + generated types.
- Tests with the agent runner mocked.

Out (YAGNI for now):
- Background watcher / autonomous processing.
- Multi-user auth / per-user request ownership.
- Remote / hosted operation.
- A separate implementer subagent (the skill covers both steps; add later only if
  plan and implement need different tool sets).

## Data model

New table `feature_requests` in `app/models.py`:

| column | type | notes |
|---|---|---|
| `id` | int pk | |
| `title` | `String(200)` | card headline |
| `description` | `Text` | operator's user story (the draft) |
| `priority` | `String(16)` | `low` \| `normal` \| `high`, default `normal` |
| `tag` | `String(64)` nullable | free area tag (e.g. `pricing`, `products`, `ui`) |
| `status` | `String(32)` | state machine below, default `draft`, indexed |
| `plan` | `Text` nullable | agent-generated markdown, operator-editable |
| `review_note` | `Text` nullable | operator note on reject; included in re-plan prompt |
| `execution_log` | `Text` nullable | captured `claude` output from the implement run |
| `branch` | `String(200)` nullable | `feat/req-{id}` |
| `pr_url` | `String(500)` nullable | |
| `error` | `Text` nullable | failure reason when status = `failed` |
| `created_at` | `DateTime(tz)` | `server_default=func.now()` |
| `updated_at` | `DateTime(tz)` | `onupdate=func.now()` |

Schema change on a new table works under `create_all` (tests) but still needs an
Alembic migration for dev/prod (repo invariant).

### State machine

```
draft ──plan──▶ planning ──▶ planned ──approve──▶ approved ──implement──▶ implementing ──▶ done
                  (agent)       │                                            (agent)      └▶ failed ──retry──▶ implementing
                          reject+note│
                                ▼
                              draft   (agent re-plans, sees review_note)
```

- `planning`, `implementing` are transient (agent is running). FE polls while in
  these states.
- Operator may `PATCH` the `plan` text while status is `planned`, before approving.
- `reject` requires a `review_note`, moves status back to `draft`; the next `plan`
  run includes the note so the agent can correct course.
- `failed` keeps `error` + partial `execution_log`; `retry` re-runs implement.

Allowed transitions are enforced in the router (reject an action if status is
wrong → HTTP 409).

## Agent bridge — `app/agent/runner.py`

Two functions, both shell out to the `claude` CLI already installed on the host:

**`generate_plan(req)`** — read-only.
- Prompt: the user story (+ `review_note` if re-planning) and an instruction to use
  the `feature-pipeline` skill to produce a repo-specific implementation plan in
  markdown, **writing no code**.
- Runs in the repo root (read-only; no branch, no worktree).
- Captures stdout → `req.plan`; status → `planned`. On error → status back to
  `draft`, `error` set.

**`implement(req)`** — writes code, isolated.
- Creates a git worktree: `git worktree add ../pz-req-{id} -b feat/req-{id}`.
  **The live working tree and the running app are never touched.**
- Prompt: the (possibly edited) `plan` + an instruction to use the
  `feature-pipeline` skill to implement it, run tests, commit, push, and open a PR,
  printing the PR URL as the final line.
- Captures stdout → `req.execution_log`; parses the PR URL → `req.pr_url`;
  `req.branch = feat/req-{id}`; status → `done`.
- On any failure → status `failed`, `error` set, `execution_log` keeps partial
  output.
- Worktree is removed in a `finally` (`git worktree remove --force`) whether the run
  succeeds or fails; the branch persists.

**Concurrency:** a single in-process lock allows **one agent run at a time**. A
second plan/implement request while one is running → HTTP 409. Marked with a
`# ponytail:` comment naming the ceiling: single-process app; move to a DB-backed
lock or a queue if concurrent runs are ever needed.

**Duration:** a claude run takes minutes, so both ops run via FastAPI
`BackgroundTasks`. The endpoint sets the transient status and returns immediately;
the FE polls the card until status changes. (This departs from the existing
synchronous `jobs.py`, which the codebase's own `# ponytail:` comment says to
revisit when the wait hurts — a multi-minute run is that point.)

## Skill — `.claude/skills/feature-pipeline/SKILL.md`

Holds the actual procedure so it lives in one editable markdown file instead of
being hardcoded in Python. Two sections:

- **Planning:** how to turn a user story into a plan for *this* repo — read
  `poolzoneV2/CLAUDE.md` and README, respect the invariants (dual pricing formula,
  generated API types, Alembic migrations, whitelist import semantics), output
  markdown, write no code.
- **Implementing:** branch naming, run the test suites before committing, follow the
  repo's lint/format rules, commit style, push, open PR with `gh`, print the PR URL
  last.

The backend prompt for each op is thin — it points `claude -p` at this skill and
passes the request's story/plan.

## Backend API — `app/api/routers/feature_requests.py`

Mirrors `jobs.py`. Pydantic I/O in `app/api/schemas.py`, registered in
`app/api/main.py`.

| method + path | purpose |
|---|---|
| `GET /api/feature-requests` | list; filter (status/tag/priority) + sort via existing `filters.py` `col:op:value` parser; `limit` |
| `GET /api/feature-requests/{id}` | detail |
| `POST /api/feature-requests` | create draft (title, description, priority, tag) |
| `PATCH /api/feature-requests/{id}` | edit plan and/or fields (allowed only in appropriate statuses) |
| `POST /api/feature-requests/{id}/plan` | start plan run (draft → planning, BackgroundTask) |
| `POST /api/feature-requests/{id}/approve` | planned → approved |
| `POST /api/feature-requests/{id}/reject` | planned → draft, requires `review_note` |
| `POST /api/feature-requests/{id}/implement` | approved/failed → implementing, BackgroundTask |

Session handling via existing `deps.get_db` (commit-on-success / rollback-on-error).

## Frontend — `frontend/src/pages/FeatureRequests.tsx`

- New nav entry in `AppShell`, route in `App.tsx`.
- **List:** card grid. Each card: status badge, title, priority, tag chip,
  truncated description, updated-at. Filter bar (status / tag / priority) + sort
  (newest / recently updated / priority). "New request" dialog (title, description,
  priority, tag).
- **Detail drawer/page:** full user story; `plan` shown as rendered markdown, and as
  an editable `<Textarea>` when status is `planned`; execution log (monospace,
  scrollable); branch + PR link; status-appropriate action buttons — Generate plan /
  Save plan / Approve / Reject (+ note) / Implement / Retry.
- Uses TanStack Query with `refetchInterval` while a card is `planning` or
  `implementing`.
- After API changes, run `npm run api:types` (repo invariant) so the typed client
  matches.

Plan editing uses a plain `<Textarea>` + markdown render, not TipTap — the plan is
markdown and a rich editor adds no value here.

## Testing — `poolzoneV2/tests/test_feature_requests.py`

- CRUD: create draft, list with filters, get detail, patch.
- Every transition, including illegal transitions returning 409.
- The agent runner (`generate_plan`, `implement`) is **mocked** — tests never spawn a
  real `claude` process or touch git.
- The concurrency lock: a second run attempt while "running" → 409.

## Constraints & risks

1. **Host prerequisites:** the backend host must have `claude` authenticated and
   `gh` authenticated with push rights to the origin. This is not "local only" in the
   pure sense — the implement→PR step reaches the remote. Documented so it isn't a
   surprise.
2. **Security:** an FE button triggers unsandboxed code generation + a push. Safe for
   a **trusted single operator on localhost**; it would be a serious hole if the FE
   were ever exposed to untrusted users. Do not expose this app publicly without
   adding auth and sandboxing.
3. **Worktree isolation** protects the live app/working tree from the implement run,
   but plan and implement runs still consume host resources and API tokens; the
   one-at-a-time lock bounds that.
```
