# M4 spec: unattended operation

Implements "Lead rotation, pausing and continuity" and the budget rules of `v1.md`. The scheduling itself is done by the agent with its scheduled-task tool; `room.py` supplies the facts, the text and the state changes around it. Same constraints as M2.

## Machine block additions

Two keys join the `agent-room-state` block in `MISSIONS.md` (the template in `templates/playbook/MISSIONS.md` gains them; unknown keys were already kept, and a missing `status` reads as `running`):

```
status: running            # running | paused | stopped | done
mission_started: none      # ISO-8601 UTC, set when a mission's spec is recorded
```

## `room.py watchdog N [--silent-after DURATION]`

Run by the watchdog scheduled task, as role `watchdog`. `DURATION` like `3h` or `45m`, default `3h` (drills use a short one).

1. Sync the state worktree (read only; the watchdog never writes state).
2. Progress time = the later of:
    - the commit time of the newest state-branch commit whose diff of `MISSIONS.md` changes the `step:` line of the machine block;
    - the committer time of the newest `mission/*` branch tip on the remote.
3. Do nothing (print why, exit 0) if `status` is `paused`, `stopped` or `done`, if `step` is `waiting for owner`, or if now minus progress time is under `DURATION`.
4. Do nothing if the room already has a `LEAD-SILENT` message newer than the progress time (one alarm per stall).
5. Otherwise `say N watchdog "LEAD-SILENT: no progress since <time> (step <step>, mission <mission>)"`, which buzzes.

Exit 0 unless an error (1). It never schedules anything.

## Handover and joining helpers

- The watchdog, `handoff` and `reconcile` all work from a checkout of the project repo or without one (the state commands' `ROOM_STATE_REMOTE`/clone path), because the watchdog's scheduled session may start anywhere.
- `room.py join-line N [--takeover]` prints the line that starts a lead: `Join agent room N in OWNER/NAME as lead, pipeline <VERSION>. Follow LEAD.md: https://github.com/SigorMatt/agent-room/blob/<VERSION>/LEAD.md`. With `--takeover` it adds `Take over the lease (lease take --takeover): the previous lead stopped without handing over.`, for the lead Matthew starts after `LEAD-SILENT`.
- `room.py handoff N --step STEP` posts `HANDOFF: mission <mission>, next step <STEP>` while it still holds the lease, then in one state write records `step`, the room cursor and `intent=none`, and releases the lease (`lease_session: none`). It prints the join line for the scheduled task, and the agent schedules it. If scheduling fails, the agent posts `NEXT-LEAD-NEEDED` (it buzzes); a released lease doesn't block that post. The successor's plain `lease take` wins, and a duplicate launch finds the lease held and stands down.
- `room.py reconcile N` prints, for a joining lead, the recorded state next to GitHub's facts: the machine block; the recorded PR's state (open, merged with its merge sha, closed); whether the room holds the recorded `ESCALATION-n`/`MERGE-HOLD-n`/`HANDOFF`; and the recorded `intent`, with a one-line hint (`intent done: clear it`, `intent not done: redo it`). It changes nothing.

## Budgets

- `room.py budget` prints the mission's elapsed time (now minus `mission_started`) against the budget of the current phase: the `Mission budget: <n> hours` phrase under the `### Phase <phase>:` heading of `PLAYBOOK.md` (the template's form), else 8 hours. Exit 0 under budget, 6 over, 1 when `mission_started` is `none`. Task attempts stay in the `MISSIONS.md` body, kept by the lead.

## Pause, stop, done

- `room.py state set status=paused|stopped|done` is used by the lead before posting `PAUSED`, `STOPPED` or `DONE`; after posting, it runs `lease release`. The watchdog then stays quiet, and the next lead joins with a plain `lease take`.

## Drill hooks

For the M6 failure drills, `PLAYBOOK.md` may carry a `drill:` line. `LEAD.md` (M5) tells the lead what each value means; `room.py` only prints it in `reconcile`:

| `drill:` | The lead |
| --- | --- |
| `stop-after-merge` | ends its session right after `room.py merge` succeeds, before any bookkeeping |
| `no-handoff` | ends at the mission boundary without `handoff` or scheduling |

## Tests

`tests/test_unattended.py`: watchdog quiet and alarm cases (paused, waiting for owner, recent step change, recent mission push, stale, existing alarm), `join-line`, `handoff` state and message, `reconcile` for each intent, `budget` under and over.
