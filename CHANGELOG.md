# Changelog

Releases are immutable tags. Each entry gives the kind of release, what changed, and every migration step with its owner. Projects pin a version in `PLAYBOOK.md`; [`STABLE`](STABLE) names the one new projects pin.

## v1.0.0 (unreleased)

**Kind:** major. The pipeline of [`docs/design/v1.md`](docs/design/v1.md) replaces the single-skill agent room and its `docs/BUILD_PLAN.md` flow.

**Added**

- `room.py` v1: session-aware messages, the role guard, hyphenated kinds, buzzes by kind, links pinned to the release.
- The `agent-room/state` branch and the lead lease, with state writes that fail when someone else wrote first.
- `preflight`: checks the repo, its protection, the state branch and the environment, for architect and lead.
- Review records: cold reviews, Qodo archives, dispositions and the ledger.
- `gate` and `merge`: the merge gate, merge holds, and a merge bound to the reviewed head commit.
- Unattended operation: `handoff` and successor leads, `intent` and `reconcile`, the watchdog, budgets, `PAUSE` and `STOP`.
- The lead task: one scheduled task per project with an API trigger, which starts every lead. `lead-task-prompt` prints its prompt, which accepts only a well-formed join line; `start-lead` starts a lead through it, posts `LEAD-STARTED`, and refuses while a lead is running or starting, or the room is closed or done, or paused or stopped (except for the architect). Matthew creates the task once per project and adds its token as `ROOM_FIRE_TOKEN_<NAME>`.
- The watchdog gains a decision alarm, `LEAD-SILENT: no lead joined after DECISION-<n>`, three hours after a `DECISION` to a parked lead that no lead answers, and reminders every 12 hours while a stall or such a wait lasts. A lead holding the lease at `waiting for owner` now counts as a stall. A failed buzz is retried at the next run, at most twice per stall. The architect starts takeovers and the lead after a decision; the watchdog starts at most one lead per stall (below).
- The watchdog tries at most one start per stall, in the run that posts the stall's first alarm, with no retries (`LEAD-STARTED: … started by watchdog`), only when no lead has shown a sign of life since the stall began: no post from a lead session that hasn't handed over, and no lease taken since. That covers a handover's successor that never came, the lead after a `DECISION` that nobody started, and a lead that died right after its progress without posting. It also needs no `LEAD-STARTED` from the architect or the watchdog for that stall, the build not paused or stopped, and the lead task configured. It never starts the phase's first lead, nor one for a lead that joined at `waiting for owner`. `start-lead --seen ID` makes the architect's starter tasks start nothing if a lead message or a `LEAD-STARTED` came after comment ID (`0` in a new room); a deliberate takeover of a lead that keeps posting leaves it out. The watchdog adds `LEAD-SILENT: still waiting for Matthew: <KIND>-<n> since <time>`, every 12 hours while a parked room recorded as current waits on an unanswered `ESCALATION` or `MERGE-HOLD`, and retries a failed `still state unreadable` buzz (M6d, B-5 and B-6).
- Starter tasks: the architect starts every lead (the first, the one after a decision, a resume and a takeover) with a one-time scheduled task that runs `start-lead N architect` in the `agent-room` environment, since an agent can't fire a task Matthew created in the web UI (finding T). Matthew approves its creation; the fallback is **Run now** on the lead task, or the Code tab.
- Parking: a lead that waits only on Matthew records it, releases the lease and ends, instead of scheduling check-ins. The architect starts the lead after his decision, and deletes the watchdog at `DONE`.
- Protocols: `ARCHITECT.md` and `LEAD.md`, and the thin skill.
- Briefs for the subagents, and manuals for Matthew with an "I want to…" index.

**Migration**

- Matthew: save the new skill in each Claude account, replacing the old one, and paste the Project instructions from `ARCHITECT.md` (section 2) into each project's Claude Project. At each project's first kickoff, set up its lead task ([Set up the lead task](docs/manual/set-up-the-lead-task.md)).
- Architect and lead: none. Rooms opened with the old skill don't carry over; start projects as `ARCHITECT.md` section 5 says.
