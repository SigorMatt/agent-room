# M6d spec: one watchdog start per stall, and reminders while a room waits on Matthew

Builds backlog items B-5 and B-6 before M7, as Matthew decided on 2026-11-16. Same constraints as M2: standard-library Python, `gh` and `curl` only.

**Why so small:** M6b's watchdog starts failed three reviews (cold R2-1, S2-1 and S3-4, all high), because the starts interacted with alarms, episodes and the decision path. This design has one rule. It runs after the existing alarm logic. It allows at most one automatic start per stall, decided against the stall's first alarm, and it stays out of the way of a lead that may still be working.

## B-5: one start per stall

The watchdog's alarm logic (`stall_alarm`, called for a pending decision and an ordinary stall) stays as it is, except that each path counts only its own alarms (below). After each of those `stall_alarm` calls, the watchdog evaluates one start rule for the same stall. The stall is identified by the same `since` that `stall_alarm` gets: the progress time, or the pending `DECISION`'s time. Before any lead joined (pre-start) the watchdog only alarms: no lead joined because the architect hasn't handed over, or Matthew's own start failed, and either way the architect decides (cold M6d R1-6).

**Its own alarms:** the decision path counts only `LEAD-SILENT: no lead joined after DECISION-n` and its `still` form; the waiting reminder only its own texts for that request; state unreadable only its newest run (B-6). The ordinary stall counts every watchdog `LEAD-SILENT` newer than its progress, as in M6b, so an alarm from an outage with no progress since stands in for it. A reminder for one request never stands in for a decision's alarm (cold M6d R1-3).

**It starts a lead when all of these hold:**
1. **Alarmed:** the stall has one of its own trusted watchdog `LEAD-SILENT`s newer than `since`, posted at this run or before, its buzz sent or failed. The oldest is the stall's *first alarm*. A start never precedes its alarm.
2. **One start per stall:** the room has no trusted `LEAD-STARTED` from the architect or the watchdog newer than `since`, confirmed or not. A lead's own handover start doesn't count: its successor is what stalled (cold M6d R1-5, qodo PR #14 finding 2).
3. **Nobody was talking:** no trusted lead message of any kind (`LEAD ONLINE`, `STATUS`, `HANDOFF` and so on) is newer than the first alarm's time minus `silent-after`.
   - A lead that posted within `silent-after` before the alarm may be working quietly (a long builder run after its `STATUS`), so the watchdog never takes it over. It only alarms and reminds, and the architect decides (cold M6d R1-4).
   - A lead message after the alarm means a lead joined or spoke: the stall had its start, by the watchdog, the architect or Matthew by hand, even if no `LEAD-STARTED` was posted for it (qodo PR #14 finding 1).
   - So once a stall's start is held off, it stays held off: the decision doesn't change at later runs (cold M6d R1-1).
4. **Not halted:** the machine block's status for this room isn't `paused`, `stopped` or `done`, whoever holds the lease. A lead that posted `PAUSED` or `STOPPED` and died before releasing the lease is not taken over: a takeover would set the status back to `running` (cold M6d R1-2).
5. **Configured:** the lead task is configured (`lead-task:` line and token).

**Starting:**
- When the rule holds, the watchdog runs `start-lead`'s logic as role `watchdog`: `--takeover` when the lease is held, plain otherwise. `start-lead` posts `LEAD-STARTED: <url> (<plain|takeover> join line, started by watchdog)`, or the unconfirmed form.
- `watchdog` comes back as a `start-lead` role, and `LEAD-STARTED` comes back into `WATCHDOG_CAN`.
- `start-lead`'s own guards still apply: room, status, lease, and the 30-minute "still starting" window. `--force` is never used.

**Outcomes:**

| `start-lead` | The watchdog |
| --- | --- |
| 0 (started, or unconfirmed with `LEAD-STARTED` posted) | Prints `started: …`. That is this stall's one start. |
| 1 (a definite failure, nothing posted) | Prints the error. The next run tries again, because rules 2 and 3 still hold. |
| 3 or 6 (refused, or not configured) | Prints a note. Nothing else: the alarm and its reminders tell Matthew. A later run starts the lead if the refusal's cause is gone (the lead task configured, say). |

**Order of operations:** the alarm is posted before the start, always, so a failed alarm post exits 1 before anything is fired. The `LEAD-STARTED` post keeps its retries and its de-duplication.

**The architect's starts and the watchdog's (cold M6d R1-1):** a stall's start can come from either, and an architect's starter task may run hours after it was created (finding U).
- The watchdog starts none after the architect's `LEAD-STARTED` (rule 2), or after any lead message following the alarm (rule 3).
- **`start-lead --seen ID`:** the architect's starter tasks pass the room's newest comment ID when the architect decided. `start-lead` then refuses (exit 3) when the room has a trusted lead message, or a trusted `LEAD-STARTED` from any role, newer than comment ID: `refused: the room moved on after #ID: <kind> #<id> at <time>; read the room again`. So a starter that runs after the watchdog's start, or after a lead joined, starts nothing.
- `--seen` is optional (a lead's handover doesn't need it). `ARCHITECT.md` 8.4 passes it in every starter task.

**Known limits:**
- **A lost `LEAD-STARTED` and no join:** if the fire worked, all three posts of `LEAD-STARTED` failed, and the lead never joined, the next run starts another. Nothing joined, so that is a second try, not a second lead.
- **Two runs at once:** the watchdog is one hourly scheduled task whose run takes about a minute, so its runs don't overlap. If two did (Matthew runs it by hand during a scheduled run), both could fire within the same seconds. The lease then lets one lead work: a plain lead finds the lease held and ends, and of two takeovers the first loses the lease and stops at its next write (qodo PR #14, finding 3).
- **A handover posted just after its progress:** a handover's `HANDOFF` and `LEAD-STARTED` come a minute or two after the step it writes. If the alarm's run falls within those minutes of `silent-after` after the step, rule 3 holds the start off, and the architect decides. Runs are hourly, so this is rare.
- **A lead that posted within `silent-after` before the alarm, then died:** no automatic start (rule 3). The alarm and reminders come as in M6b, and the architect decides.

**What it means per path:**
- **An ordinary stall** (the lease held by a dead lead, or released after a handover whose successor never came or joined and died): one takeover or plain start after the first alarm, if no lead posted within `silent-after` before it. If that lead also dies before progress, it's the same stall: reminders, no second start.
- **A lead that joined at `waiting for owner` and died** (cold M6b R1-1): `since` is that lead's `LEAD ONLINE`, a new stall, so one takeover is allowed.
- **A pending `DECISION`:** if the architect started no lead, the watchdog starts one plain lead after its "no lead joined after DECISION-n" alarm, which comes `silent-after` after the decision. If the architect's start failed, its `LEAD-STARTED` counts, and the watchdog only reminds.
- **Pre-start:** alarm and reminders only, as in M6b.

The watchdog task's prompt doesn't change: room.py does the posting and starting. Its environment must be `agent-room`, because it needs the token.

## B-6: reminders while a room waits on Matthew

**Waiting-for-Matthew reminder:**
- **When it applies:**
  - the step starts with `waiting for owner`;
  - the lease is released (a parked lead);
  - room N is recorded as the current room, in `PLAYBOOK.md` or the machine block (a room nothing records gets no reminder, qodo PR #14, finding 6);
  - the room's newest trusted lead request, an `ESCALATION-n` or `MERGE-HOLD-n`, has no trusted `DECISION-n` after it.
- **What it posts:** once `REMINDER_AFTER` × `silent-after` (12 hours by default) has passed since that request, `LEAD-SILENT: still waiting for Matthew: <KIND>-<n> since <time> (step <step>)`. It does this through `stall_alarm`, with `since` = the request's time and that text as both first and reminder, so it repeats every 12 hours under the same failed-buzz retry rules. Only its own reminders for that request count as this stall's alarms; a state unreadable alarm posted while it waited doesn't delay it (qodo PR #14, finding 5).
- **No start:** Matthew must decide.
- **Why:** this catches a request whose own buzz was lost (ntfy's limit, cold M6b R3-8 and S4-4), and an owner who forgot.

**State unreadable:** a `still state unreadable` reminder whose buzz failed is posted again at the next run, at most `BUZZ_RETRIES` times, like other reminders (cold M6b S4-2). Simplest is to route that alarm through `stall_alarm` too, keeping its texts. As before M6d, only the newest run of state unreadable alarms counts, the ones after the stall's last other alarm: an outage that comes back after an ordinary alarm gets a new first alarm (qodo PR #14, finding 4).

## Docs

- **`LEAD.md`:** no change, except where it says the watchdog never starts leads. It may start one takeover per stall.
- **`ARCHITECT.md`:**
  - **9.5:** after a `LEAD-SILENT`, look for the watchdog's `LEAD-STARTED`. If there is one, wait for its `LEAD ONLINE` (about 30 minutes, the bullet on a recent `LEAD-STARTED`). If there's none, the watchdog may still start one at a later run (it retries a failed fire, and starts once the lead task is configured), or it is holding off for good (a lead posted within `silent-after` before the alarm, or the build is paused or stopped). Decide by hand as now; a starter task passes `--seen`, so whichever start comes first is the only one. A second stall alarm or a reminder after the watchdog's start means its lead failed too; the watchdog won't start another for that stall. A lead with a recent `STATUS` is never taken over by the watchdog: the architect decides, as now (cold M6d R1-4).
  - **9.2:** if the architect doesn't start the lead after a decision, the watchdog does, `silent-after` later. The starter task passes `--seen`.
  - **8.4:** every starter task runs `start-lead N architect [--takeover] --seen <ID>`, with the room's newest comment ID when the architect decided; a recreated starter keeps the same ID. Kickoff (section 8 and `docs/manual/kick-off-a-phase.md`): the watchdog alarms before the first lead joins, and starts leads only after one has joined (cold M6d R1-6, which also fixes the stale "alarms only" texts).
  - **9.5's cross-reference** to the 30-minute bullet points at the right bullet (cold M6d R1-7).
  - **9.1 table:** the waiting-for-Matthew reminder.
- **Manuals:** answer-a-buzz, message-kinds (the watchdog posts `LEAD-STARTED` again), troubleshooting, glossary, stop-or-pause (no watchdog start while paused or stopped, whoever holds the lease), kick-off-a-phase.
- **`docs/design/m6b-lead-relay.md`:** one note that M6d brings one watchdog start per stall back (B-5).
- **`BUILD-STATE.md`:** B-5 and B-6 done.
- **`CHANGELOG.md`.**

## Tests

All offline, in `tests/test_relay.py` or a new `tests/test_m6d.py`.

**B-5:**
- A start after the alarm, in each path: stall with the lease held (takeover), stall with the lease released (plain), decision, and a lead that joined at waiting and died.
- Pre-start: the alarm and reminders, no start.
- No start without an alarm; a waiting reminder for another request doesn't stand in for a decision's alarm.
- No second start for the same stall: after a watchdog start, an architect start, an unconfirmed start, or a lead that joined after the alarm with no `LEAD-STARTED` posted.
- A start after a handover whose successor never joined, and after one whose successor joined and died.
- No start when a lead posted within `silent-after` before the first alarm (a `STATUS` before a long builder run), at that run or any later run.
- No start while the status is `paused` or `stopped` and the lease is still held.
- `start-lead --seen ID`: refused after a lead message or any `LEAD-STARTED` newer than ID (the watchdog's start, say); starts when nothing newer came.
- A definite failure is retried at the next run.
- Not configured (6) and refused (3) print a note only.
- A watchdog run never fires more than once.
- The alarm is posted before the fire; a failed alarm post means no fire.

**B-6:**
- The waiting reminder comes at 12 hours, repeats, and retries a failed buzz.
- No reminder once a `DECISION` came, or while the lease is held.
- No start on this path.
- The state-unreadable reminder retry, and a new first alarm for an outage that comes back after an ordinary alarm.
- A state unreadable alarm during the wait doesn't delay the waiting reminder.
- No reminder when no room is recorded.
