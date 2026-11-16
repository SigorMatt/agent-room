# M6d spec: one watchdog start per stall, and reminders while a room waits on Matthew

Builds backlog items B-5 and B-6 before M7, as Matthew decided on 2026-11-16. Same constraints as M2: standard-library Python, `gh` and `curl` only.

**Why so small:** M6b's watchdog starts failed three reviews (cold R2-1, S2-1 and S3-4, all high), because the starts interacted with alarms, episodes and the decision path. This design has one rule. It runs after the existing alarm logic, which it doesn't change. It allows exactly one automatic start per stall.

## B-5: one start per stall

The watchdog's alarm logic (`stall_alarm`, called for pre-start, a pending decision and an ordinary stall) stays exactly as it is. After each `stall_alarm` call, the watchdog evaluates one start rule for the same stall. The stall is identified by the same `since` that `stall_alarm` gets: the progress time, the pending `DECISION`'s time, or `None` before any lead joined.

**It starts a lead when all of these hold:**
1. **Alarmed:** the stall already has a trusted watchdog `LEAD-SILENT` newer than `since` (any room alarm, for pre-start). This may be the one just posted, and it's counted even if its buzz failed. A start never precedes its alarm.
2. **One start per stall:** the room has no trusted `LEAD-STARTED` from any role newer than `since` (any `LEAD-STARTED` at all, for pre-start). A start by the architect counts too, and so does an unconfirmed one.
3. **Nobody is talking:** the room has no trusted lead message of any kind (`LEAD ONLINE`, `STATUS` and so on) newer than now minus `silent-after`. A lead that has just joined, or is still talking, is never displaced. A lead that loops while talking keeps getting alarms and reminders, and the architect decides.
4. **Configured:** the lead task is configured (`lead-task:` line and token).

**Starting:**
- When the rule holds, the watchdog runs `start-lead`'s logic as role `watchdog`: `--takeover` when the lease is held, plain otherwise. `start-lead` posts `LEAD-STARTED: <url> (<plain|takeover> join line, started by watchdog)`, or the unconfirmed form.
- `watchdog` comes back as a `start-lead` role, and `LEAD-STARTED` comes back into `WATCHDOG_CAN`.
- `start-lead`'s own guards still apply: room, status, lease, and the 30-minute "still starting" window. `--force` is never used.

**Outcomes:**

| `start-lead` | The watchdog |
| --- | --- |
| 0 (started, or unconfirmed with `LEAD-STARTED` posted) | Prints `started: …`. That is this stall's one start. |
| 1 (a definite failure, nothing posted) | Prints the error. The next run tries again, because rule 2 still holds. |
| 3 or 6 (refused, or not configured) | Prints a note. Nothing else: the alarm and its reminders tell Matthew. |

**Order of operations:** the alarm is posted before the start, always, so a failed alarm post exits 1 before anything is fired. The `LEAD-STARTED` post keeps its retries and its de-duplication.

**What it means per path:**
- **An ordinary stall** (the lease held by a dead lead, or released after a handover whose successor never came): one takeover or plain start after the first alarm. If that lead also dies before progress, it's the same stall: reminders, no second start.
- **A lead that joined at `waiting for owner` and died** (cold M6b R1-1): `since` is that lead's `LEAD ONLINE`, a new stall, so one takeover is allowed.
- **A pending `DECISION`:** if the architect started no lead, the watchdog starts one plain lead after its "no lead joined after DECISION-n" alarm, which comes `silent-after` after the decision. If the architect's start failed, its `LEAD-STARTED` counts, and the watchdog only reminds.
- **Pre-start:** after the 12-hour alarm, one plain start if no `LEAD-STARTED` exists in the room.

The watchdog task's prompt doesn't change: room.py does the posting and starting. Its environment must be `agent-room`, because it needs the token.

## B-6: reminders while a room waits on Matthew

**Waiting-for-Matthew reminder:**
- **When it applies:**
  - the step starts with `waiting for owner`;
  - the lease is released (a parked lead);
  - the room's newest trusted lead request, an `ESCALATION-n` or `MERGE-HOLD-n`, has no trusted `DECISION-n` after it.
- **What it posts:** once `REMINDER_AFTER` × `silent-after` (12 hours by default) has passed since that request, `LEAD-SILENT: still waiting for Matthew: <KIND>-<n> since <time> (step <step>)`. It does this through `stall_alarm`, with `since` = the request's time and that text as both first and reminder, so it repeats every 12 hours under the same failed-buzz retry rules.
- **No start:** Matthew must decide.
- **Why:** this catches a request whose own buzz was lost (ntfy's limit, cold M6b R3-8 and S4-4), and an owner who forgot.

**State unreadable:** a `still state unreadable` reminder whose buzz failed is posted again at the next run, at most `BUZZ_RETRIES` times, like other reminders (cold M6b S4-2). Simplest is to route that alarm through `stall_alarm` too, keeping its texts.

## Docs

- **`LEAD.md`:** no change, except where it says the watchdog never starts leads. It may start one takeover per stall.
- **`ARCHITECT.md`:**
  - **9.5:** after a `LEAD-SILENT`, look for the watchdog's `LEAD-STARTED`. If there is one, wait for its `LEAD ONLINE` (about 30 minutes). If there's none, the watchdog was held off (a lead is talking), refused, or not configured: decide by hand, as now. A second stall alarm or a reminder after the watchdog's start means its lead failed too; the watchdog won't start another for that stall.
  - **9.2:** if the architect doesn't start the lead after a decision, the watchdog does, `silent-after` later.
  - **9.1 table:** the waiting-for-Matthew reminder.
- **Manuals:** answer-a-buzz, message-kinds (the watchdog posts `LEAD-STARTED` again), troubleshooting, glossary.
- **`docs/design/m6b-lead-relay.md`:** one note that M6d brings one watchdog start per stall back (B-5).
- **`BUILD-STATE.md`:** B-5 and B-6 done.
- **`CHANGELOG.md`.**

## Tests

All offline, in `tests/test_relay.py` or a new `tests/test_m6d.py`.

**B-5:**
- A start after the alarm, in each path: stall with the lease held (takeover), stall with the lease released (plain), decision, pre-start, and a lead that joined at waiting and died.
- No start without an alarm.
- No second start for the same stall: after a watchdog start, an architect start, or an unconfirmed start.
- No start while any lead message is under `silent-after` old.
- A definite failure is retried at the next run.
- Not configured (6) and refused (3) print a note only.
- A watchdog run never fires more than once.
- The alarm is posted before the fire; a failed alarm post means no fire.

**B-6:**
- The waiting reminder comes at 12 hours, repeats, and retries a failed buzz.
- No reminder once a `DECISION` came, or while the lease is held.
- No start on this path.
- The state-unreadable reminder retry.
