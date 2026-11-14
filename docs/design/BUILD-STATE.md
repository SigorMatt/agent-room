# v1 build state

The build of the agent-room pipeline v1, as designed in [`v1.md`](v1.md). A fresh session can resume the build from this file alone: read `v1.md`, then this file, then issue #4.

- **Owner:** Matthew. Wants minimal intervention: buzz only for a blocker that changes the design, or "ready for your run".
- **Build lead:** the Claude session that wrote the design. It works the way the pipeline will: milestone PRs into `main`, builder subagents, a fresh cold reviewer per PR, Qodo per `QODO-REVIEW.md`, merged by the lead.
- **Status room:** issue #4 in this repo. STATUS comments only.
- **ntfy topic:** set in Matthew's `agent-room` cloud environment and known to the build lead. Not written here.

## Milestones

| # | Milestone | Status |
| --- | --- | --- |
| M0 | Commit design and build state | Done (#5) |
| M1 | Platform check | In progress |
| M2 | Core machinery | In progress (builders running; spec `m2-room-cli.md`) |
| M3 | Review records, `gate` and `merge` (spec `m3-reviews-gate.md`) | Not started |
| M4 | Unattended operation (spec `m4-unattended.md`) | Not started |
| M5 | Protocols (`ARCHITECT.md`, `LEAD.md`, briefs, thin skill), manuals and index | Not started |
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
| 1 | Merge a PR through the proxy, naming the expected head commit | Pass: a wrong head sha gets 409; #5 merged naming its head sha |
| 2 | Push `mission/*`, task branches and `agent-room/state` | Pass: no prefix needed. **Finding A** below |
| 3 | Read branch protection, rulesets and bypass | Pass on a public repo. **Finding B** below |
| 4 | A session schedules its successor; it gets the repo, runs without approvals, uses the right environment | Pass except the environment: the scheduled session started in auto mode with no approval prompts, had the caller's repos checked out with push access, and had `create_trigger`, `send_later`, `list_triggers` and `Agent`, but not `add_repo` (**Finding E**). It ran in the caller's environment, so a lead started from Matthew's `agent-room` environment getting its variables is checked in M6 |
| 5 | Recurring watchdog task, at acceptable cost | Pending |
| 6 | The architect chat can start a subagent and create a scheduled task | Pass: the build lead is a Claude chat in a Project, and did both |
| 7 | Resuming a subagent keeps its context | Pass |
| 8 | Worktree isolation for parallel builders | Pass: worktrees under `.claude/worktrees/`, branch `worktree-agent-<id>` |
| 9 | A waiter survives an idle hour | Pending (probe, 85 minutes) |
| 10 | Qodo's bot login and comment format match `QODO-REVIEW.md` | Pass: on the M0 PR, `qodo_review.py` found the Summary and Code Review comments from `qodo-code-review[bot]`, the commit marker equal to the head, and 5 findings matching the header counts |
| 11 | A buzz reaches Matthew's phone | Sent from the build chat (HTTP 200). Receipt and the lead environment: pending |

### Findings that change the build

- **A. Branches can't be deleted through the proxy**, neither by `git push --delete` nor by the API. So:
    - builders never push; the lead merges their worktree branches locally, and only mission branches reach GitHub;
    - mission branches are removed by GitHub's "Automatically delete head branches" setting, which preflight checks and asks Matthew to turn on once per repo;
    - two probe branches remain in this repo (`mission/M0-probe`, `agent-room/state`) for Matthew to delete when convenient.
- **B. Private repos on GitHub Free can't have branch protection or rulesets** (the API answers 403, "upgrade to GitHub Pro"). Preflight treats only that answer, a 403 whose message asks to upgrade, as "no protection", which passes. Any other 403 (missing permission, token scope) fails the check.
- **D. Subagents can't read the Claude Project.** Builders, cold reviewers and Qodo readers can't load the Projects tool, so `QODO-REVIEW.md` is copied byte for byte into `docs/QODO-REVIEW.md`. The Project copy stays Matthew's master; changes reach the repo by PR.
- **E. A scheduled session has no `add_repo`.** It inherits the repos of the session that scheduled it. So a lead schedules its successor from a session that already has the project repo, which every lead does.
- **F. Builder worktrees start from the default branch,** not from the lead's current branch. A builder on a mission first merges the mission branch into its worktree branch, and every brief says so.
- **C. A new repo may be completely empty** (`pet-todo` has no commits). Preflight detects this, and the architect's kickoff creates the first commit on `main`; no protection can exist yet, so this is safe.

## Decisions taken during the build

| Date | Decision | Why |
| --- | --- | --- |
| 2026-11-14 | Builders work in local worktrees and never push | Finding A; also removes stale-builder pushes after `STOP` |
| 2026-11-14 | The lead pushes the mission branch after each merged task; the watchdog counts a step change or a mission-branch push as progress | Follows from builders never pushing (Qodo PR #5) |
| 2026-11-14 | The platform check ran in this repo, not a scratch repo, and its results live here, not in the checkboxes of `v1.md` | The design's checklist stays the list of assumptions (Qodo PR #5) |
| 2026-11-14 | Docs-only milestone PRs get Qodo but no cold review | The design's coverage rule covers code changes only; the design itself had two cold reviews |
| 2026-11-14 | The protocols, briefs and thin skill move from the core milestone to M5, after the code they describe | Keeps each milestone PR reviewable; `v1.md` stays the authority meanwhile |
| 2026-11-14 | Mission PRs merge with a merge commit, not a squash | Keeps every `fixed in <sha>` reachable from `main` after the branch is deleted |
| 2026-11-15 | The lease is released at `HANDOFF`, `PAUSED`, `STOPPED` and `DONE`; `lease take` fails while another session holds it, unless `--takeover`, which only a lead Matthew starts after `LEAD-SILENT` uses | Makes "only one successor can win the lease" hold for launches minutes apart, not only for simultaneous pushes (cold M2 R1-3) |

## Deferred to later milestones

| ID | Item | Milestone | From |
| --- | --- | --- | --- |
| B-1 | The gate exempts only known review-record file patterns under `reviews/`, not the whole directory, so code placed there can't skip coverage | M3 | Qodo PR #5, "Review exemption by directory lets code skip coverage" |
