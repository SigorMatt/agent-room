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
| M2 | Core machinery | Done (#6) |
| M3 | Review records, `gate` and `merge` (spec `m3-reviews-gate.md`) | Done (#7) |
| M4 | Unattended operation (spec `m4-unattended.md`) | Done (#8) |
| M5 | Protocols (`ARCHITECT.md`, `LEAD.md`, briefs, thin skill), manuals and index | Done (#9) |
| M6 | Dress rehearsal on `pet-todo` (build lead plays the architect) | Done: phase 1 of pet-todo complete (#2, #3, #4), `DONE` buzz received; findings L to P; waiting on Matthew's decision on successor starts |
| M6b | Leads started through the lead task's API trigger (`start-lead`), parking while waiting on Matthew, an alarm-only watchdog with reminders (option 1 below; watchdog starts deferred, B-5) | Done (#11): 3 cold rounds, 4 scoped reviews, 5 Qodo fetches; B-5 and B-6 deferred |
| M6c | Rehearsal of M6b on pet-todo phase 2 (build lead plays the architect) | Done: phase 2 complete (pet-todo #6, #7, #8), two unattended `start-lead` handovers, takeover by starter task; findings T, U, V |
| M6d | The watchdog starts one lead per stall, only for a lead that never came (B-5, A-12), and reminds Matthew of a room waiting on him (B-6) (spec `m6d-watchdog.md`) | Done (#14): 4 cold rounds, 2 scoped reviews, 5 Qodo fetches (6 findings resolved); `start-lead --seen` and `--replacing` for the architect's starters; finding W |
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

## Owner to-dos (Matthew)

| Since | To-do | Steps | Status |
| --- | --- | --- | --- |
| 2026-11-15 | Buy a paid ntfy.sh plan, so buzzes stop failing on the shared-IP limit (finding M) | [Handle ntfy limit errors](../manual/handle-ntfy-limit-errors.md), step 3: create an access token, add it to the `agent-room` environment as a network secret for `ntfy.sh` (or as `ROOM_NTFY_TOKEN`), then [test the buzz](../manual/test-the-buzz.md). Before M7 | Open |

## Platform check

Results of the eleven assumptions in `v1.md` ("To verify"). Evidence lives in issue #4 and in the commits of the PR that closes M1.

| # | Assumption | Result |
| --- | --- | --- |
| 1 | Merge a PR through the proxy, naming the expected head commit | Pass: a wrong head sha gets 409; #5 merged naming its head sha |
| 2 | Push `mission/*`, task branches and `agent-room/state` | Pass: no prefix needed. **Finding A** below |
| 3 | Read branch protection, rulesets and bypass | Pass on a public repo. **Finding B** below |
| 4 | A session schedules its successor; it gets the repo, runs without approvals, uses the right environment | Pass except the environment: the scheduled session started in auto mode with no approval prompts, had the caller's repos checked out with push access, and had `create_trigger`, `send_later`, `list_triggers` and `Agent`, but not `add_repo` (**Finding E**). It ran in the caller's environment, so a lead started from Matthew's `agent-room` environment getting its variables is checked in M6 |
| 5 | Recurring watchdog task, at acceptable cost | Pass: an hourly task fired on schedule (22:36:13Z), ran 22 seconds in auto mode with no approval prompts and posted on issue #4; then deleted. At one run every three hours, about eight short sessions a day. **Finding G** below |
| 6 | The architect chat can start a subagent and create a scheduled task | Pass: the build lead is a Claude chat in a Project, and did both |
| 7 | Resuming a subagent keeps its context | Pass |
| 8 | Worktree isolation for parallel builders | Pass: worktrees under `.claude/worktrees/`, branch `worktree-agent-<id>` |
| 9 | A waiter survives an idle hour | Fail for detached processes: about two minutes after the probe session's turn ended, its container was suspended and restarted (uptime 0 at the check), killing a `nohup` logger. The disk survived, and a `send_later` wake-up arrived on time. The pre-approved fallback applies (**Finding H**). Whether a command started with the harness's own background option survives: second probe pending |
| 10 | Qodo's bot login and comment format match `QODO-REVIEW.md` | Pass: on the M0 PR, `qodo_review.py` found the Summary and Code Review comments from `qodo-code-review[bot]`, the commit marker equal to the head, and 5 findings matching the header counts |
| 11 | A buzz reaches Matthew's phone | Sent from the build chat (HTTP 200). Receipt and the lead environment: pending |

### Findings that change the build

- **A. Branches can't be deleted through the proxy**, neither by `git push --delete` nor by the API. So:
    - builders never push; the lead merges their worktree branches locally, and only mission branches reach GitHub;
    - mission branches are removed by GitHub's "Automatically delete head branches" setting, which preflight checks and asks Matthew to turn on once per repo;
    - Matthew deleted the two probe branches and the merged mission branches, and turned on auto-delete in both repos (2026-11-15).
- **B. Private repos on GitHub Free can't have branch protection or rulesets** (the API answers 403, "upgrade to GitHub Pro"). Preflight treats only that answer, a 403 whose message asks to upgrade, as "no protection", which passes. Any other 403 (missing permission, token scope) fails the check.
- **D. Subagents can't read the Claude Project.** Builders, cold reviewers and Qodo readers can't load the Projects tool, so `QODO-REVIEW.md` is copied byte for byte into `docs/QODO-REVIEW.md`. The Project copy stays Matthew's master; changes reach the repo by PR.
- **E. A scheduled session has no `add_repo`.** It inherits the repos of the session that scheduled it. So a lead schedules its successor from a session that already has the project repo, which every lead does.
- **F. Builder worktrees start from the default branch,** not from the lead's current branch. A builder on a mission first merges the mission branch into its worktree branch, and every brief says so.
- **G. Deleting a scheduled task deletes every session it started.** So a successor's one-time task is never deleted (it disables itself after firing), and a session started by a task can't delete that task (`update_trigger` with `enabled=false` stops it instead). The watchdog's runs are short, so deleting it at `DONE` is safe; the lead that deletes it was not started by it.
- **H. An idle session's container is suspended within minutes.** Detached processes die; files survive; `send_later` wakes the session. So the lead never relies on a waiter alone: whenever it ends a turn waiting (for Matthew, Qodo or anything slow), it schedules a `send_later` check-in, and the watchdog catches the rest. This is the pre-approved fallback for check 9. (Since M6b, leads no longer schedule check-ins: they wait in the foreground and park; findings O and Q.)
- **I. Scheduled sessions have fewer tools.** A session started by a scheduled task had no background option on its Bash tool (idle probe 2, issue #4), so a lead started as a successor can't run a background waiter at all. The lead protocol therefore assumes only: foreground `room wait` with a timeout under ten minutes, `send_later` check-ins, and builders run in the background only if its Agent tool offers that, else one at a time (pre-approved fallback). Which Agent options a scheduled session has is checked in M6. (Since M6b, leads no longer schedule check-ins: they wait in the foreground and park; findings O and Q.)
- **J. A subagent writing under `.claude/` with the file tool can stall on an approval prompt** that an unattended session never answers (an M5 writer waited half an hour on `.claude/skills/agent-room/SKILL.md`). Briefs that touch `.claude/` tell the builder to write through Python in the shell; `LEAD.md` says so for any project file under `.claude/`.
- **K. Creating a scheduled task from an interactive session asks Matthew for approval** (at night, in the morning, and several times on 2026-11-15, which he approved as they came), while sessions started by a scheduled task run in auto mode. So the first lead Matthew starts from the Code tab should run in a mode that doesn't ask, or its handover waits for him; the lead checks the successor task's approval setting (`LEAD.md` section 6).
- **L. A scheduled task created from a Code-tab session comes out bare:** no permission mode (its runs ask for approval) and no repository source. Tasks created from a Cowork chat (this build chat, an architect chat) carry the chat's repos and auto mode. So a Code-tab lead can't start an unattended successor: it disables the task and posts `NEXT-LEAD-NEEDED` (`LEAD.md` 6), and Matthew starts the next lead by hand. The Code tab's own mode picker (Auto, the default) doesn't change this. Seen at both M6 handovers.
- **M. Free ntfy is rate-limited per IP, and cloud sessions share their outgoing IPs,** so a lead's buzz can fail with "daily limit for this shared IP" through no traffic of ours. Seen in M6 on `NEXT-LEAD-NEEDED`. `room.py` reports it and supports `ROOM_NTFY_TOKEN`; a paid plan is Matthew's decision.
- **N. A task created from a chat runs in that chat's environment.** The pet-todo watchdog was created from this build chat, which isn't in Matthew's `agent-room` environment, so its buzz found no topic. The architect must create the watchdog in the `agent-room` environment (`ARCHITECT.md` 8.4 says so); the build chat can't choose environments.
- **O. A session started by a scheduled task has no scheduling tools at all** (probe 4, issue #4): no `create_trigger`, `send_later`, `update_trigger`, `delete_trigger` or `list_triggers`; only the session-local `CronCreate`. It does inherit the creating chat's repos and the given environment (both repos checked out, ntfy topic set) and runs in auto mode. So a lead started by a task can't schedule its successor, can't schedule check-ins, and can't delete the watchdog. (Probe 1 on 2026-11-14 saw these tools in a scheduled session started in this chat's default environment; with Matthew's environment they were absent.) Probe 5b (issue #4) narrowed it: in the `agent-room` environment the scheduling connector is missing while the Docs connector loads.
- **P. One scheduled watchdog run missed an alarm.** The 20:14Z run succeeded but posted nothing, while the same command run by hand at 20:21Z alarmed correctly (no progress for 1h36m). Its output isn't visible from here. Also, while buzzes can't work (no topic in the watchdog's environment), every run re-alarms, by design of the failed-buzz retry.
- **Q. A session can start a scheduled task through its API trigger** (probes 6 and 7, issue #4). A session in the `agent-room` environment POSTed to the task's `/fire` endpoint with the token from `ROOM_FIRE_TOKEN` (HTTP 200, no block, no approval); the run started at once, in auto mode, in the task's environment with its repository, and received the fire text intact. Starting a task from this chat with `fire_trigger` works the same way. API triggers and tokens can only be made in the web UI, so Matthew creates each project's lead task there once.
- **R. A run of a task created in the web UI has `add_repo` and a GitHub connector, and its `gh` reaches only the task's repositories** (probe 6b posted to agent-room issue #4 through the connector after attaching the repo). A lead's room is in its own repository, so this doesn't matter for leads; M6c confirms it with real leads.
- **S. An agent can edit only the scheduled tasks it created.** `update_trigger` on a task Matthew made in the web UI fails ("created via http_api, not by an agent"), so he edits the lead task himself, and the architect gives him the prompt text.
- **T. An agent can't fire a task Matthew created in the web UI either** (`fire_trigger` fails: "Agents can only fire routines they created"). So the architect can't start the lead task with a fire action. It creates a one-time *starter task* in the `agent-room` environment that runs `room.py start-lead N architect` (Matthew approves the creation), as M6c's first lead was started on 2026-11-16.
- **U. An approval pop-up can wait for hours, and a one-time task whose start time has passed can't be created** (`run_once_at must be in the future`). The M6c takeover starter waited about 4 hours for Matthew and then failed, and a second request was needed. So starter tasks run 10 minutes ahead, the architect announces the pop-up, and it recreates the task at once if the time passed (`ARCHITECT.md` 8.4).
- **V. Every scheduled-task run has a `PushNotification` tool, whatever the task's push setting** (probes 8a and 8b, issue #4: "Mobile push requested"). But its pushes don't reach Matthew's phone mid-run: he saw only a notification when a run ended, titled with the session's first words. So it can't replace ntfy, and the paid ntfy plan stays the owner to-do.
- **W. A cloud session's container can restart mid-session** (the build lead's own session, three times on the evening of 2026-11-16, each while the session was idle and waiting on background work). The conversation goes on, and files on disk survive, uncommitted worktree edits included. Background subagents and background shell commands stop. The session is woken with a notice naming them, and a stopped subagent can be resumed from its saved transcript by sending it a message; a shell command is lost. Scheduled `send_later` check-ins are server-side and fire as planned. Git state, the lease and the room are untouched. For a lead: a builder it runs in the background is stopped, not failed; LEAD.md's "resume a builder; if resuming fails, start a fresh one with the full brief" covers it, but doesn't name the notice or the worktree's partial edits (B-7). Not yet seen: a restart during a turn that is running, and how often restarts happen.
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
| 2026-11-15 | The lease is released at `HANDOFF` (`handoff` records the step and cursor, posts `HANDOFF`, then releases), `PAUSED`, `STOPPED` and `DONE`; `lease take` fails while another session holds it, unless `--takeover`, which only a lead Matthew starts after `LEAD-SILENT` uses | Makes "only one successor can win the lease" hold for launches minutes apart, not only for simultaneous pushes (cold M2 R1-3) |
| 2026-11-15 | Matthew buys a paid ntfy plan (owner to-do above) | Finding M: the free plan loses buzzes on shared cloud IPs |
| 2026-11-15 | Leads start through one lead task per project with an API trigger (option 1), chosen by Matthew after probes 6 and 7 | No approvals, no machine to run, immediate starts; the alternatives stay listed under "Successor-start options" |
| 2026-11-16 | The watchdog in M6b only alarms, with a 12-hour reminder while a stall lasts and an alarm when no lead joins after a `DECISION`; it starts no leads. Takeovers and the lead after a decision are started by the architect (fire action), as before M6b but without the Code tab. Automatic watchdog starts are deferred (B-5) | Three cold reviews of the watchdog's start rules (R2-1, S2-1, S3-4: all high) each found new interactions between starts, alarms and the decision path; the handover start, which matters most, stays automatic |
| 2026-11-16 | Matthew: build B-5 and B-6 before M7 (M6d) | B-5 with a deliberately small rule (one start per stall, after its alarm) so it can be verified |

## Assumptions while Matthew was away (from 2026-11-15 01:24)

Calls the build lead made that Matthew would normally make. Each is reversible; Matthew reviews them on his return.

| # | Assumption | Why | To reverse |
| --- | --- | --- | --- |
| A-1 | Lease release and `--takeover` (decision 2026-11-15) refine v1's lease rules without changing the design's intent | v1 requires a single winning successor; the cold review showed the plain rule doesn't give one | Drop `--takeover` and release; accept duplicate leads |
| A-2 | Milestones M3 and M4 are built and reviewed in parallel with M2, each on the previous one's branch, and merged in order | Saves hours; each still gets its own cold reviews, PR, Qodo and merge | Build them one after another |
| A-3 | Low-severity findings from a scoped review that touch rare edge paths may be deferred to the next milestone already in flight (B-2 to M4) instead of looping more scoped reviews | v1 allows deferral to a later mission; keeps reviews converging | Fix them in the same milestone |
| A-4 | No buzz overnight unless the build is blocked | Matthew is asleep and asked to be told on return | — |
| A-5 | The lease is the machine block of the latest state commit whose block parses; `room.py` refuses any commit that breaks the block or changes the lease outside `lease take`/`release` | Three scoped reviews showed that a lenient reading of a broken block either locks out a takeover or lets a superseded lead through | Accept a stuck lead when the block is hand-damaged |
| A-6 | Low-severity gate findings that assume a hostile lead are fixed only when the fix is small; the gate is a mechanical aid for a cooperative lead | Keeps M3 converging; v1 leaves scope to the lead's judgement | Harden further in a patch release |
| A-7 | Probe 3 (what a scheduled session's Agent tool can do) wasn't created: creating a scheduled task suddenly asked for approval at night. The protocol covers both answers, and M6 checks it | Matthew asleep | Run the probe when Matthew is back |
| A-8 | For the M6 rehearsal the build lead wrote pet-todo's design and playbook as architect, without Matthew's review | M6 is the build lead's rehearsal; M7 is Matthew's own run | — |
| A-9 | For M6c the build lead wrote pet-todo phase 2 (D-2 to D-4, items P2-1 to P2-4), with one question deliberately left open (Q-1, the busy-lock behaviour) so the lead escalates, and answers it as architect | The rehearsal needs a real escalation and a lead that parks | — |
| A-10 | M6c's watchdog runs hourly with `--silent-after 60m`. A one-time kickoff at 04:00Z was to start the first lead overnight; it found M6b unmerged and did nothing. Since the watchdog starts no leads (decision 2026-11-16), M6c runs in the daytime: the build lead, as architect, starts the first lead, takeovers and the lead after its `DECISION` with the fire action, and Matthew approves each pop-up | Firing the lead task from this chat needs Matthew's approval (finding K), and the chat has no `ROOM_FIRE_TOKEN_*` | Delete the kickoff task (spent) |
| A-11 | Scoped reviews S2 and S3 found high findings after the last round; the build lead fixed and re-reviewed (S2), then removed the feature behind them (S3, decision above) instead of holding the PR for Matthew | Matthew asleep; the fix narrows scope and returns to v1's watchdog-alarms-only behaviour | Restore watchdog starts from PR #11's history |
| A-12 | After Qodo PR #14 and cold M6d rounds 1 and 2, the build lead narrowed B-5 to one principle: the watchdog starts a lead only when no lead has shown a sign of life (a post from, or a lease take by, a session that hasn't handed over) since the stall began, i.e. the lead it expected never came (a handover's successor, the lead after a `DECISION`, a lead that died right after its progress). It tries once per stall, in the run that posts the stall's first alarm, with no retries (Qodo PR #14 finding 1, Action required: the alarm, posted first, records the attempt). None while paused or stopped, none before the first lead joined, none for a lead that joined at `waiting for owner`. `start-lead --seen ID` (plain) and `--replacing SESSION` (takeover) let the architect's starter tasks stand down once the room moved on, and a takeover of a paused or stopped build needs `--force` | Matthew had approved B-5, not its details. The watchdog can't tell a dead lead from one in a long builder run, and every looser rule tried (M6b, M6d round 1) was found to take over working leads or chain starts. Each change makes the watchdog start less often, never more | Widen the rule (spec m6d-watchdog.md, B-5), e.g. a takeover after 4 x silent-after of silence |

## M6 dress rehearsal results (2026-11-15)

pet-todo phase 1, three missions, four lead generations, in about 4.5 hours of wall time (most of it waiting for handovers).

| Check | Result |
| --- | --- |
| Lead joins, plans, makes main green (Phase 0 behaviour) | Pass: planner, `PLAN`, M1 made the test command pass |
| Missions end to end (spec, builders, cold rounds, scoped reviews, Auditor, PR, Qodo, gate, merge) | Pass: pet-todo #2, #3, #4, each 10 to 20 minutes |
| Handover between missions | Partly: handoff and lease release correct; the successor couldn't start unattended (findings L, O) |
| Successor started from the architect side with Matthew's environment | Pass: lead 3 and the takeover lead joined with repo, topic and auto mode |
| Drill: push code after review | Pass: the lead spotted the owner commit and ran a scoped cold review before merging |
| Drill: kill the lead right after a merge | Pass: lead 3 stopped after merging; `LEAD-SILENT` (by hand, finding P); the takeover lead took the lease, finished the bookkeeping, posted `DONE` and closed the room |
| Watchdog deletion at `DONE` | Fail in the lead (finding O); the architect deleted it |
| Buzz | Partly: `NEXT-LEAD-NEEDED` failed on the free ntfy limit (finding M); `DONE` arrived |
| Drills not run | Second lead while one runs, Qodo not reviewing, `CHANGE-n` during Build (missions built too fast), lead looping (unit-tested only), an escalation (none was needed) |

**Open question:** who starts successors. See "Successor-start options" below.

## M6c rehearsal results (2026-11-16)

pet-todo phase 2, room 5: three missions, four lead generations, 08:48Z to 17:08Z. About four of those hours were spent waiting for one approval (finding U).

| Check | Result |
| --- | --- |
| First lead started by the architect | Pass: a starter task running `start-lead 5 architect` (after `fire_trigger` was refused, finding T); `LEAD ONLINE` 1 minute after the start |
| Escalation and decision | Pass, by a better path than planned: the lead escalated Q-1 while planning and kept building M4 and M5; `DECISION-1` was ACKed within 2 minutes; no park was needed |
| Drill: stop after merge | Pass: the M4 lead stopped after merging pet-todo #6; the watchdog posted `LEAD-SILENT` 69 minutes later (`--silent-after 60m`, hourly runs) |
| Takeover | Pass: a starter task with `--takeover` (generation 6), which finished M4's bookkeeping in 1 minute |
| Unattended handovers | Pass, twice: generation 6 to 7 in 50 seconds, and 7 to 8 in about 1 minute, both through `start-lead` with no human |
| `CHANGE-1` | Pass: posted during M5's cold review (its build had already finished), ACKed, built as a new task, reviewed and merged |
| Phase end | Pass: `DONE`, room closed, lease released; the architect deleted the watchdog |
| Buzzes | Partly: `ESCALATION-1` arrived; the watchdog's `LEAD-SILENT` failed on ntfy's 429 shared-IP limit (finding M; owner to-do) |
| Approvals Matthew gave | Three: the first start, the takeover (asked twice, finding U), and the watchdog deletion |
| Not exercised | A park and the lead after a decision (the lead never parked); the decision alarm; reminder alarms |

## Successor-start options (2026-11-15)

What the pipeline needs: something that starts a lead in auto mode, in the `agent-room` environment, with the repos, without Matthew's approval, when a handover, a stall or an owner decision happens. It needn't be the architect, or an LLM. Matthew chose to test option 1 first; the others are kept here to come back to if it doesn't work as envisioned.

| # | Option | How it works | For | Against | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | **One lead task per project, started through its API trigger** | A scheduled task with no schedule, in the `agent-room` environment with the repos; its prompt accepts only a well-formed join line passed as fire text. Matthew adds an API trigger and puts its token in the environment as `ROOM_FIRE_TOKEN`. A lead starts its successor with one `POST …/v1/claude_code/routines/<task>/fire`; the watchdog starts takeover leads; the architect (or "Run now") starts the lead after a `DECISION` | Stays in Anthropic's sandbox on the subscription; no machine to run; no approvals; starts are immediate; small protocol change | Research preview (beta header may change); 30 fires an hour per task; the token is an environment variable sessions can read, because network secrets are never attached to `api.anthropic.com` | **Works** (findings Q, R); chosen, built in M6b |
| 1b | Variant: a GitHub trigger instead of a token | The lead labels the room issue; an "Issue" GitHub trigger starts the task | No token | Needs the Claude GitHub App on each repo; hourly event caps; no issue filters, so every issue event starts a short run | Not tested |
| 2 | Architect chat as dispatcher (option A of the M6 summary) | The architect chat keeps `send_later` check-ins during a phase and creates each lead with `create_trigger` and `environment_id` | Proven in M6 (lead 3, the takeover lead) | Up to 30 minutes per start; check-ins in Matthew's design chat; creating a task there asks Matthew to approve (finding K) | Fallback |
| 3a | An always-on machine of Matthew's (laptop, or a paid VPS) running the leads | Claude Code CLI with `--dangerously-skip-permissions` and Remote Control; a cron script runs a dispatch check and launches `claude -p "<join line>"`; the watchdog is cron too; ntfy self-hosted or paid | Full control; no cloud tool gaps; a VPS costs about €5–15 a month and doesn't depend on home power or network | Matthew maintains it; security is his (dedicated VM or user, a fine-grained GitHub token for the project repos only); leads lose the cloud environment, secrets and GitHub proxy, so a bigger rework; a laptop sleeps and moves networks | Fallback if 1 fails |
| 3b | The same machine only dispatches, starting cloud leads | `claude --cloud "<join line>"` from a checkout; `/remote-env` sets the CLI's default environment | Leads stay in the cloud | Whether `--cloud` sessions start in auto mode is undocumented; needs a probe | Not tested |
| 4 | GitHub Actions as dispatcher, optionally as lead host | A workflow the lead triggers at handover, plus a scheduled workflow as watchdog, running Claude Code with a subscription token | Ephemeral, isolated runners; free minutes; no machine | GitHub's scheduled runs often start late; 6-hour job cap; leads leave the Claude cloud, as in 3a | Not tested |
| 5 | Matthew starts each lead (option B), or the API-billed Agent SDK | One tap and a paste per mission, or per-token billing | Nothing to build | Matthew's time, or cost for multi-agent missions | Last resort |

## Deferred to later milestones

| ID | Item | Milestone | From |
| --- | --- | --- | --- |
| B-1 | The gate exempts only known review-record file patterns under `reviews/`, not the whole directory, so code placed there can't skip coverage | M3 | Qodo PR #5, "Review exemption by directory lets code skip coverage" |
| B-2 | (Done in M2 after Qodo PR #6 flagged it as Action required.) Stale state worktrees, from cold M2 scoped-1: say when local work is moved aside and keep its commits (S1-3); recognise the project checkout and stale state worktrees whatever the current directory, with a marker file in the worktree's git dir (S1-4, S1-5) | M4 | cold M2 S1-3, S1-4, S1-5 |
| B-3 | (Done in M2 after Qodo PR #6.) Strict machine-block parsing, from cold M2 scoped-3: the block is the only `agent-room-state` block and the first fenced block, its body only `key: value` or blank lines, closed by a bare fence; a second such block is refused on commit; a repair never deletes text, it prepends a fresh block and retires the damaged fence (S3-1, S3-2, S3-3) | M4 | cold M2 S3-1, S3-2, S3-3 |
| B-4 | (Done: M3 spec, and `LEAD.md` in M5.) The M3 spec and `LEAD.md` say that a cold finding of weakened tests is a sensitive-area hold (reason 5) by the lead's judgement; the gate holds only deleted tests mechanically | M3 | Qodo PR #6, "Weakened tests evade the merge hold" |
| B-5 | (Done in M6d: at most one try per stall, in the run of its first alarm, with no retries, only when no lead has shown a sign of life since the stall began, never while paused or stopped, never for a lead that joined at `waiting for owner`, and no pre-start start; `start-lead --seen` for the architect's plain starters and `--takeover --replacing` for its takeovers; a takeover of a halted build refused without `--force`.) Watchdog starts leads by itself (takeover after a stall, the lead after a `DECISION`), with rules simple enough to verify: the M6b attempt is in PR #11's history and its reviews under `reviews/cold/M6/` | after v1 | cold M6b R2-1, S2-1, S3-4 |
| B-6 | (Done in M6d: it names the newest open request and lists the others.) The watchdog reminds Matthew of a parked room waiting on him with no `DECISION` (every 12 hours), so a lost `ESCALATION`/`MERGE-HOLD` buzz is caught; and a failed `still state unreadable` reminder is retried at the next run like other reminders | M7 | cold M6b R3-8, S4-2, S4-4 |
| B-7 | LEAD.md: on a "container restarted" notice, a stopped builder is resumed by message (or started fresh with the full brief if that fails), after checking its worktree's uncommitted edits; a stopped foreground wait is run again; nothing posted or merged is redone | M7 | finding W |
