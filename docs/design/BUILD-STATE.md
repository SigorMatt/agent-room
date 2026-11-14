# v1 build state

The build of the agent-room pipeline v1, as designed in [`v1.md`](v1.md). A fresh session can resume the build from this file alone: read `v1.md`, then this file, then issue #4.

- **Owner:** Matthew. Wants minimal intervention: buzz only for a blocker that changes the design, or "ready for your run".
- **Build lead:** the Claude session that wrote the design. It works the way the pipeline will: milestone PRs into `main`, builder subagents, a fresh cold reviewer per PR, Qodo per `QODO-REVIEW.md`, merged by the lead.
- **Status room:** issue #4 in this repo. STATUS comments only.
- **ntfy topic:** set in Matthew's `agent-room` cloud environment and known to the build lead. Not written here.

## Milestones

| # | Milestone | Status |
| --- | --- | --- |
| M0 | Commit design and build state | In progress |
| M1 | Platform check | In progress |
| M2 | Core machinery | Not started |
| M3 | Reviews and merge gate | Not started |
| M4 | Unattended operation | Not started |
| M5 | Manuals and index | Not started |
| M6 | Dress rehearsal on `pet-todo` (build lead plays the architect) | Not started |
| M7 | Matthew's owner run, then tag `v1.0.0` | Not started |

## Pre-approved fallbacks (Matthew, 2026-11-14)

Applied without asking. Stop and ask only if the lead cannot merge PRs at all, or scheduled tasks do not work at all.

| If the check finds | Then |
| --- | --- |
| A lead can't schedule its successor | Fallback buzz: Matthew starts the next lead |
| Branch pushes need a prefix | Adopt the prefix |
| Worktrees don't work for builders | Builders run one at a time |
| Resuming a builder doesn't work | Fresh builder with the full brief |
| A waiter dies when the machine idles | Rely on the watchdog and scheduled check-ins |

## Platform check

Results of the eleven assumptions in `v1.md` ("To verify"). Evidence lives in issue #4 and in the commits of the PR that closes M1.

| # | Assumption | Result |
| --- | --- | --- |
| 1 | Merge a PR through the proxy, naming the expected head commit | Pending (tested on the M0 PR) |
| 2 | Push `mission/*`, task branches and `agent-room/state` | Pass: no prefix needed. **Finding A** below |
| 3 | Read branch protection, rulesets and bypass | Pass on a public repo. **Finding B** below |
| 4 | A session schedules its successor; it gets the repo, runs without approvals, uses the right environment | Partly: a chat session created a one-time task with no approval prompt, in auto mode. Repo access and tools in the started session: pending (probe, issue #4) |
| 5 | Recurring watchdog task, at acceptable cost | Pending |
| 6 | The architect chat can start a subagent and create a scheduled task | Pass: the build lead is a Claude chat in a Project, and did both |
| 7 | Resuming a subagent keeps its context | Pass |
| 8 | Worktree isolation for parallel builders | Pass: worktrees under `.claude/worktrees/`, branch `worktree-agent-<id>` |
| 9 | A waiter survives an idle hour | Pending (probe, 85 minutes) |
| 10 | Qodo's bot login and comment format match `QODO-REVIEW.md` | Pending (tested on the M0 PR) |
| 11 | A buzz reaches Matthew's phone | Sent from the build chat (HTTP 200). Receipt and the lead environment: pending |

### Findings that change the build

- **A. Branches can't be deleted through the proxy**, neither by `git push --delete` nor by the API. So:
    - builders never push; the lead merges their worktree branches locally, and only mission branches reach GitHub;
    - mission branches are removed by GitHub's "Automatically delete head branches" setting, which preflight checks and asks Matthew to turn on once per repo;
    - two probe branches remain in this repo (`mission/M0-probe`, `agent-room/state`) for Matthew to delete when convenient.
- **B. Private repos on GitHub Free can't have branch protection or rulesets** (the API answers 403, "upgrade to GitHub Pro"). Preflight treats that answer as "no protection", which passes.
- **C. A new repo may be completely empty** (`pet-todo` has no commits). Preflight detects this, and the architect's kickoff creates the first commit on `main`; no protection can exist yet, so this is safe.

## Decisions taken during the build

| Date | Decision | Why |
| --- | --- | --- |
| 2026-11-14 | Builders work in local worktrees and never push | Finding A; also removes stale-builder pushes after `STOP` |
