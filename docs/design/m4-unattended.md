# M4 spec: unattended operation

Implements "Lead rotation, pausing and continuity" and the budget rules of `v1.md`. The scheduling itself is done by the agent with its scheduled-task tool; `room.py` supplies the facts, the text and the state changes around it. Same constraints as M2.

## Machine block additions

Two keys join the `agent-room-state` block in `MISSIONS.md` (the template in `templates/playbook/MISSIONS.md` gains them; unknown keys were already kept, and a missing `status` reads as `running`):

```
status: running            # running | paused | stopped | done
mission_started: none      # ISO-8601 UTC, set when a mission's spec is recorded
```

`state set` accepts only those four statuses and an ISO-8601 time (or `none`) for `mission_started`. `lease take` sets `status: running` in its own write, so a halted status never outlives the next lead. It leaves `waiting_for_owner` alone, since a successor may join while the owner still hasn't answered. A state write that changes `step` or `pr` sets `waiting_for_owner` back to `no`, unless that same write sets it, and the watchdog ignores a flag once anything has progressed since it was set.

## `room.py watchdog N [--silent-after DURATION]`

Run by the watchdog scheduled task, as role `watchdog`. `DURATION` like `3h` or `45m`, default `3h` (drills use a short one).

0. Pre-start: while room N holds no trusted lead `LEAD ONLINE`, no lead has joined it, and the state may be missing (phase 1's kickoff, before `state init-lead`) or still the previous phase's. The watchdog then stays quiet with the note `no lead has joined room N yet`, whatever the status, flags or state say. Once 12 hours have passed since the room's issue was opened with still no lead, it alarms once: `LEAD-SILENT: no lead has joined room N in 12h`. After a lead has joined, the steps below apply. (M6b adds a 12-hour reminder to this alarm and to every stall, `LEAD-SILENT: still no lead has joined room N` here: see [`m6b-lead-relay.md`](m6b-lead-relay.md).)
1. Sync the state worktree (read only: it fetches and reads git objects; the watchdog never writes state). If the pushed machine block is damaged, the last valid one in the branch's history stands in (M2's `pushed_lease`). If there is no state at all (`ls-remote` lists no state branch, or no valid block exists anywhere in its history), it raises the alarm `LEAD-SILENT: state unreadable (<reason>)` instead, under the same `DURATION`, measured from the last state-branch commit, if any. It is deduped only against an earlier `state unreadable` alarm that is the room's newest alarm, never against an ordinary stall alarm. Any other failure to read it (a fetch that breaks on the network) exits 1 without posting, and the next run tries again.
2. Do nothing (print why, exit 0) if:
    - `status` is `paused`, `stopped` or `done`, in any case, and the lease is released (`lease_session: none`). With the lease still held, the lead may have died between writing the status and posting and releasing, so it counts as running, with a note. A status recorded for another room (the block's `room` isn't the current room) never silences;
    - `step` starts with `waiting for owner`;
    - room N isn't the current room (`PLAYBOOK.md`'s `room:`, else the block's `room`, the same helper the gate uses): the watchdog is left from an earlier phase, and the note says to delete it.
3. Progress time = the latest of these, and nothing else (v1: progress, not chatter):
    - the commit time of the newest state-branch commit whose `MISSIONS.md` changes `step` or `pr` in the machine block (`merge` records `pr`); a commit whose block doesn't parse changes nothing;
    - the committer time of the newest `mission/*` branch tip on the remote;
    - the merge time of the newest merged PR whose head is a `mission/*` branch of this repo (GitHub deletes the branch on merge). Closed PRs are read per branch (`head=OWNER:<branch>`), page by page, for the remote's `mission/*` branches, the recorded mission's branch as `MISSIONS.md` names it, and the recorded PR's head, so no number of other PRs can hide a merge.

    Lease takes, handoffs at the same step, intents, the counter and the cursor are chatter, so a lead in a loop gets an alarm.
4. Do nothing if `waiting_for_owner` is `yes` and nothing has progressed since the commit that set it. Progress after that commit makes the flag stale, and the watchdog measures normally, with a note. Otherwise do nothing if now minus progress time is under `DURATION`.
5. Do nothing if the room already has a trusted watchdog `LEAD-SILENT` newer than the progress time (one alarm per stall), unless that alarm says `(buzz failed`.
6. Otherwise buzz first (click: the room), then post `LEAD-SILENT: no progress since <time> (step <step>, mission <mission>) (buzz sent)`, or `(buzz failed: <reason>)`, with `--no-buzz`. An alarm whose buzz failed doesn't count in step 5, so the next run tries again.

Exit 0 unless an error (1). It never schedules anything.

## Handover and joining helpers

- The watchdog, `handoff` and `reconcile` all work from a checkout of the project repo or without one (the state commands' `ROOM_STATE_REMOTE`/clone path), because the watchdog's scheduled session may start anywhere.
- `room.py join-line N [--takeover]` prints the line that starts a lead: `Join agent room N in OWNER/NAME as lead, pipeline <VERSION>. Follow LEAD.md: https://github.com/SigorMatt/agent-room/blob/<VERSION>/LEAD.md`, where `<VERSION>` is the pin in `PLAYBOOK.md` (else `room.py`'s own), as v1's pin rule says. With `--takeover` it adds `Take over the lease (lease take --takeover): the previous lead stopped without handing over.`, for the lead Matthew starts after `LEAD-SILENT`.
- `room.py handoff N --step STEP --cursor ID` works in three steps, all while it holds the lease until the last: (a) one state write records `step`, `cursor` = `ID` and `intent=none`; (b) it posts `HANDOFF: mission <mission>, next step <STEP>`, with a second paragraph saying the successor is being scheduled and `NEXT-LEAD-NEEDED` follows if that fails; (c) it releases the lease (`lease_session: none`). If (a) fails, nothing is posted. If (c) fails, it prints the error and `HANDOFF is posted; run 'lease release' again`, and exits 1. `ID` is the last comment the lead acted on (from a `[cursor: ID]` line it handled), or `none`, and must be a comment of room N; the local cursor file isn't used, because the waiter moves it on reading. It prints the join line for the scheduled task, and the agent schedules it. If scheduling fails, the agent posts `NEXT-LEAD-NEEDED` (it buzzes); a released lease doesn't block that post. The successor's plain `lease take` wins, even after losing a push to an unrelated write, and a duplicate launch finds the lease held and stands down.
- `room.py intent N "<intent>"` records an intent before the outside action (it needs the lease). Room N must be the current room (exit 1 otherwise). A `post <KIND>` intent is recorded as `post <KIND> in room N after #<ID>`, where `ID` is room N's last comment, and `close room` as `close room N after #<ID>`; any other intent is recorded as given.
- `room.py reconcile N` prints, for a joining lead, the recorded state next to GitHub's facts: the machine block; the recorded PR's state (open, merged with its merge sha, closed); whether the room holds the recorded `ESCALATION-n`/`MERGE-HOLD-n` (and its `DECISION-n`) and the latest `HANDOFF`; and the recorded `intent`, with a one-line hint (`intent done: clear it`, `intent not done: redo it`, or `intent unknown`). It changes nothing. Its PR facts count only PRs whose head is in this repo, by a trusted author, into `main`. The intents it judges:
    - `merge PR #<n> at <sha>` (as `merge` records it): done once merged; open, redo it; closed without merging, it can't be merged, so clear the intent and reopen or escalate.
    - `open PR <branch>` or `open PR for M<k>`: done if such a PR is open or merged; one closed without merging means opening a new one.
    - `post <KIND> in room <n> after #<ID>`: done if a trusted lead message of that kind in room `n` has a larger comment ID, whichever room reconcile runs for. No clocks are involved. Without `after`, only a numbered kind can be judged.
    - `close room N after #<ID>`: done only if the issue is closed and a trusted lead `DONE` or `STOPPED` has a larger comment ID than `ID`, posted before the close (as the protocol does) or after it. Recorded without an ID, the `DONE` or `STOPPED` must come after the issue closed. For another room than the one reconcile runs for, the hint is `intent from an earlier room: clear it` (it is left in the block after a phase's `DONE`).

## Budgets

- `room.py budget` prints the mission's elapsed time (now minus `mission_started`) against the budget of the current phase: the `Mission budget: <n> hours` phrase under the `### Phase <phase>:` heading of `PLAYBOOK.md` (the template's form), else 8 hours. It reads the phrase tolerantly: markdown emphasis around the label or the number, `h`, `hr`, `hrs`, `hour` or `hours`, and decimals. Exit 0 under budget, 6 over, 1 when `mission_started` is `none`. Task attempts stay in the `MISSIONS.md` body, kept by the lead.

## Pause, stop, done

- `room.py state set status=paused|stopped|done` is used by the lead before posting `PAUSED`, `STOPPED` or `DONE`; after posting, it runs `lease release`. The watchdog then stays quiet, and the next lead joins with a plain `lease take`, which sets `status` back to `running`.

## Drill hooks

For the M6 failure drills, `PLAYBOOK.md` may carry a `drill:` line. `LEAD.md` (M5) tells the lead what each value means; `room.py` only prints it in `reconcile`:

| `drill:` | The lead |
| --- | --- |
| `stop-after-merge` | ends its session right after `room.py merge` succeeds, before any bookkeeping |
| `no-handoff` | ends at the mission boundary without `handoff` or scheduling |

## Tests

`tests/test_unattended.py`: watchdog quiet and alarm cases (paused, waiting for owner, recent step change, recent mission push, stale, existing alarm), `join-line`, `handoff` state and message, `reconcile` for each intent, `budget` under and over. Each fix below has its regression test there, in `tests/test_room.py` (trust) or in `tests/test_state.py` (stale state worktrees).

## Changes after cold review round 1

From `reviews/cold/M4/round-1.md`, plus deferral B-2 from the M2 scoped review:

- **R1-1:** progress also counts any state write but the cursor's, and merges of mission PRs.
- **R1-2:** `lease take` sets `status: running`.
- **R1-3:** the watchdog buzzes first and marks the alarm `(buzz sent)` or `(buzz failed: …)`; a failed one is retried on the next run.
- **R1-4:** reconcile's PR facts count only this repo's PRs by a trusted author into `main`.
- **R1-5:** `handoff` takes `--cursor ID` and records it.
- **R1-6:** `ROOM_TRUST` adds logins to the gh login instead of replacing it, as v1 says.
- **R1-7:** fixed on M2 by R2-5 (a plain `lease take` retries after losing a push to an unrelated write), merged here.
- **R1-8 to R1-10:** the watchdog's quiet rules above: status in any case, `waiting_for_owner` and a step starting `waiting for owner`, and another room.
- **R1-11, R1-12:** the hints for closed PRs and for `close room`.
- **R1-13, R1-14:** `room.py intent`, and post intents judged by comment ID.
- **R1-15:** the tolerant budget phrase.
- **B-2 (cold M2 S1-3, S1-4, S1-5):** when `room.py` creates a state worktree or clone, it writes a marker file, `agent-room-state`, into that worktree's own git dir. Only a directory with the marker, or one whose `.git` file names a git dir that is gone, is ever moved aside and rebuilt, whatever the current directory. Anything else (the project checkout, a builder's worktree, a clone made by hand) is refused with a message. The project checkout that worktrees are added to is found before anything moves, so a stale worktree can be rebuilt from inside it. Before a stale worktree is moved aside, its HEAD and uncommitted changes are saved as a commit on `refs/agent-room/broken-<UTC timestamp>` in its repository (the project's, for a linked worktree), or else as a patch file next to the moved directory, and the notice says which.

## Changes after cold review round 2

From `reviews/cold/M4/round-2.md`, after merging M2's last-valid-block reading:

- **R2-1:** `lease take`, and any state write that moves `step` without setting the flag, set `waiting_for_owner` back to `no`.
- **R2-2:** the current room is `PLAYBOOK.md`'s first, then the block's, through one helper shared with the gate.
- **R2-3:** progress is only a `step` or `pr` change, a mission push or a mission PR's merge; the loop drill alarms.
- **R2-4:** a halted status silences the watchdog only once the lease is released.
- **R2-5:** a damaged block falls back to the last valid one; no state at all raises `LEAD-SILENT: state unreadable (<reason>)`.
- **R2-6:** `close room` needs a trusted lead `DONE` or `STOPPED` after the close.
- **R2-7:** `intent` refuses a room that isn't the current one, and post intents name their room.
- **R2-8:** a moved-aside linked worktree loses its `.git` file, so it holds plain files and git there can't reach the rebuilt worktree, which gets the same admin dir name; its work is on the ref, and the notice says so.

## Changes after cold review scoped 1

From `reviews/cold/M4/scoped-1.md`:

- **S1-1:** `waiting_for_owner: yes` mutes the watchdog only while nothing has progressed since the commit that set it, and a `pr` change resets the flag like a `step` change.
- **S1-2:** only a missing state branch (per `ls-remote`) or no valid block raises `state unreadable`; a transient read failure exits 1 and the next run retries.
- **S1-3:** `intent N "close room"` records `close room N`; reconcile judges it against that room, and one for another room gets `intent from an earlier room: clear it`.
- **S1-4, S1-5:** the pre-start rule (step 0): quiet until a trusted lead `LEAD ONLINE` in room N, then one alarm 12 hours after the room opened with no lead; a status recorded for another room never silences.

## Changes after Qodo PR #8

From `reviews/qodo/PR-8/1/`, each claim checked against the code first:

- **A lost state branch gets no new alarm:** a `state unreadable` alarm is deduped only against an earlier `state unreadable` alarm that is the newest alarm, never against an ordinary stall alarm.
- **Some recent merges trigger stall alarms:** merges are found per mission branch (`head=OWNER:<branch>`), page by page, not in one page of 100 closed PRs.
- **A failed handoff leaves a false notice:** `handoff` records step, cursor and `intent=none`, then posts `HANDOFF`, then releases the lease. A failed record write posts nothing; a failed release prints `HANDOFF is posted; run 'lease release' again` and exits 1.
- **Completed phases appear to need closing:** `close room` intents record `close room N after #<ID>`, and a later trusted lead `DONE` or `STOPPED` counts whether it came before or after the close.
- **A waiting successor gets a false silence alarm:** `lease take` no longer resets `waiting_for_owner` (this reverses part of R2-1); step and pr changes, and S1-1's progress-after-flag rule, end a stale flag.
