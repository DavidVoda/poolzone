---
name: feature-runner
description: Pick up feature requests the operator has marked ready, and run a subagent per request to plan or implement them locally. Invoke when the operator says "run the feature runner", "process feature requests", "check for requests to plan/implement", or after they flip a request to ready_for_plan / ready_for_impl.
---

# Feature Runner

You (an interactive local claude session) are the runner. The poolzoneV2 admin app
holds feature requests; the operator flips them to `ready_for_plan` or
`ready_for_impl` in the UI. Your job: pull those, run **one subagent per request**
to do the work in the **current checkout / current branch (no commit)**, then move
the request's status via the API.

The admin API is at `http://localhost:8000` (adjust if the operator runs another
port). No auth — localhost only.

> **Future:** a periodic/cron agent will call this same skill on a timer so the
> operator doesn't have to. Not built yet — for now the operator triggers you by
> hand. Keep every step here idempotent (claim-before-work via the status guard) so
> a timer can reuse it unchanged.

## Procedure

1. **Find work.** Fetch both queues:
   ```bash
   curl -s "http://localhost:8000/api/feature-requests?status=ready_for_plan"
   curl -s "http://localhost:8000/api/feature-requests?status=ready_for_impl"
   ```
   If both are empty, tell the operator "nothing ready" and stop.

2. **For each `ready_for_plan` request** (do them one at a time):
   a. **Claim it** (guards against double-runs):
      ```bash
      curl -s -X POST http://localhost:8000/api/feature-requests/<id>/transition \
        -H 'content-type: application/json' -d '{"to":"planning"}'
      ```
      A 409 means someone already claimed it — skip.
   b. **Dispatch a subagent** (Agent tool, `general-purpose`) with a prompt like:
      "Read `.claude/skills/feature-pipeline/SKILL.md` and follow its PLANNING
      section. User story (title `<title>`): `<description>`. If `<review_note>` is
      set, address it. Output ONLY the plan as markdown. Write no code." Pass the
      request's `title`, `description`, `review_note` from step 1's JSON.
   c. **Store the plan + advance:**
      ```bash
      curl -s -X POST .../<id>/transition -H 'content-type: application/json' \
        -d "$(jq -n --arg p "<plan markdown>" '{to:"planned", plan:$p}')"
      ```
      On subagent failure, send it back with the error instead:
      `{"to":"ready_for_plan","error":"<what failed>"}`.

3. **For each `ready_for_impl` request** (one at a time):
   a. **Claim:** `{"to":"implementing"}` (409 → skip).
   b. **Dispatch a subagent** (Agent tool, `general-purpose`): "Read
      `.claude/skills/feature-pipeline/SKILL.md` and follow its IMPLEMENTING section.
      Implement this plan in the current checkout, no commit: `<plan>`. Report the
      files you changed and the verification results." Pass the request's `plan`.
   c. **On success:** `{"to":"implemented","execution_log":"<subagent summary>"}`.
      **On failure:** `{"to":"ready_for_impl","error":"<what failed>"}` and leave the
      partial changes in the tree for the operator.

4. **Report** to the operator: per request, what happened (planned / implemented /
   failed + why), and — for implemented ones — remind them the changes are
   **uncommitted in the working tree**, ready for their review + commit.

## Rules

- **One subagent per request per phase.** Never batch multiple requests into one
  subagent — isolation keeps failures contained.
- **Never commit, push, or branch.** The subagent writes to the working tree; the
  operator owns git.
- Claim (status → planning/implementing) **before** dispatching, so a re-run or a
  future timer can't double-process the same request.
- If the subagent's plan/impl touches the pricing formula, generated API types, or a
  DB column, the feature-pipeline skill already tells it to handle the invariant —
  trust that, but sanity-check the report.
