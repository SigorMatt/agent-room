# M4 spec: unattended operation

Implements "Lead rotation, pausing and continuity" and the budget rules of `v1.md`. The scheduling itself is done by the agent with its scheduled-task tool; `room.py` supplies the facts, the text and the state changes around it. Same constraints as M2.

## Machine block additions

Two keys join the `agent-room-state` block in `MISSIONS.md` (the template in `templates/playbook/MISSIONS.md` gains them; unknown keys were already kept, and a missing `status` reads as `running`):

```
status: running            # running | paused | stopped | done
mission_started: none      # ISO-8601 UTC, set when a mission's spec is recorded
```

`state set` accepts only those four statuses and an ISO-8601 time (or `none`) for `mission_started`. `lease take` sets `status: running` in its own write, so a status left at `paused`, `stopped` or `done` never outlives the next lead.

## `room.py watchdog N [--silent-after DURATION]`

Run by the watchdog scheduled task, as role `watchdog`. `DURATION` like `3h` or `45m`, default `3h` (drills use a short one).

1. Sync the state worktree (read only: it fetches and reads git objects; the watchdog never writes state).
2. Do nothing (print why, exit 0) if:
    - `status` is `paused`, `stopped` or `done`, in any case (any other value counts as running);
    - `waiting_for_owner` is `yes`, or `step` starts with `waiting for owner`;
    - room N isn't the room the state records (the block's `room`, else `PLAYBOOK.md`'s): the watchdog is left from an earlier phase, and the note says to delete it.
3. Progress time = the latest of:
    - the commit time of the newest state-branch commit whose `MISSIONS.md` changes a machine-block key other than `cursor` (so `merge`'s `intent` and `pr` count, and reading the room doesn't);
    - the committer time of the newest `mission/*` branch tip on the remote;
    - the merge time of the newest merged PR whose head is a `mission/*` branch of this repo (GitHub deletes the branch on merge).
4. Do nothing if now minus progress time is under `DURATION`.
5. Do nothing if the room already has a trusted watchdog `LEAD-SILENT` newer than the progress time (one alarm per stall), unless that alarm says `(buzz failed`.
6. Otherwise buzz first (click: the room), then post `LEAD-SILENT: no progress since <time> (step <step>, mission <mission>) (buzz sent)`, or `(buzz failed: <reason>)`, with `--no-buzz`. An alarm whose buzz failed doesn't count in step 5, so the next run tries again.

Exit 0 unless an error (1). It never schedules anything.

## Handover and joining helpers

- The watchdog, `handoff` and `reconcile` all work from a checkout of the project repo or without one (the state commands' `ROOM_STATE_REMOTE`/clone path), because the watchdog's scheduled session may start anywhere.
- `room.py join-line N [--takeover]` prints the line that starts a lead: `Join agent room N in OWNER/NAME as lead, pipeline <VERSION>. Follow LEAD.md: https://github.com/SigorMatt/agent-room/blob/<VERSION>/LEAD.md`, where `<VERSION>` is the pin in `PLAYBOOK.md` (else `room.py`'s own), as v1's pin rule says. With `--takeover` it adds `Take over the lease (lease take --takeover): the previous lead stopped without handing over.`, for the lead Matthew starts after `LEAD-SILENT`.
- `room.py handoff N --step STEP --cursor ID` posts `HANDOFF: mission <mission>, next step <STEP>` while it still holds the lease, with a second paragraph saying the successor is being scheduled and `NEXT-LEAD-NEEDED` follows if that fails. Then in one state write it records `step`, `cursor` = `ID` and `intent=none`, and releases the lease (`lease_session: none`). `ID` is the last comment the lead acted on (from a `[cursor: ID]` line it handled), or `none`, and must be a comment of room N; the local cursor file isn't used, because the waiter moves it on reading. It prints the join line for the scheduled task, and the agent schedules it. If scheduling fails, the agent posts `NEXT-LEAD-NEEDED` (it buzzes); a released lease doesn't block that post. The successor's plain `lease take` wins, even after losing a push to an unrelated write, and a duplicate launch finds the lease held and stands down.
- `room.py intent N "<intent>"` records an intent before the outside action (it needs the lease). A `post <KIND>` intent is recorded as `post <KIND> after #<ID>`, where `ID` is room N's last comment; any other intent is recorded as given.
- `room.py reconcile N` prints, for a joining lead, the recorded state next to GitHub's facts: the machine block; the recorded PR's state (open, merged with its merge sha, closed); whether the room holds the recorded `ESCALATION-n`/`MERGE-HOLD-n` (and its `DECISION-n`) and the latest `HANDOFF`; and the recorded `intent`, with a one-line hint (`intent done: clear it`, `intent not done: redo it`, or `intent unknown`). It changes nothing. Its PR facts count only PRs whose head is in this repo, by a trusted author, into `main`. The intents it judges:
    - `merge PR #<n> at <sha>` (as `merge` records it): done once merged; open, redo it; closed without merging, it can't be merged, so clear the intent and reopen or escalate.
    - `open PR <branch>` or `open PR for M<k>`: done if such a PR is open or merged; one closed without merging means opening a new one.
    - `post <KIND> after #<ID>`: done if a trusted lead message of that kind has a larger comment ID. No clocks are involved. Without `after`, only a numbered kind can be judged.
    - `close room`: done only if the issue is closed and a trusted lead message came after it closed.

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
