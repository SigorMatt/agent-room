# M6d spec: one watchdog start per stall, and reminders while a room waits on Matthew

Builds backlog items B-5 and B-6 before M7, as Matthew decided on 2026-11-16. Same constraints as M2: standard-library Python, `gh` and `curl` only.

**Why so small:** M6b's watchdog starts failed three reviews (cold R2-1, S2-1 and S3-4, all high), because the starts interacted with alarms, episodes and the decision path. This design has one rule. It runs after the existing alarm logic. It allows at most one automatic start per stall, and only where no lead has shown a sign of life since the stall began, so it never displaces a lead that may still be working.

## B-5: one start per stall, only for a lead that never came

**The principle (after cold rounds 1 and 2):** the watchdog can't tell a dead lead from one running a long foreground builder. So it starts a lead only when no lead has shown a sign of life since the stall began: the lead it expected never came. A lead that has spoken or taken the lease since then may be working, and the architect decides, as in M6b.

Two cases are what the start is for:
- a handover whose successor never came;
- a `DECISION` after which nobody started the lead.

A third is covered by the same rule: a lead that made progress and died before posting anything.

**Where it runs:** after `stall_alarm` on two paths only, the ordinary stall and the pending decision, with the same `since`: the progress time, or the pending `DECISION`'s time. The other paths only alarm and remind, as in M6b:
- pre-start: no lead joined, because the architect hasn't handed over or Matthew's own start failed (cold M6d R1-6);
- a lead that joined at `waiting for owner` and holds the lease: each lead started there would begin a new stall, so starts would chain without bound (cold M6d R2-4);
- the waiting reminder;
- state unreadable.

**Its own alarms:** the decision path counts only `LEAD-SILENT: no lead joined after DECISION-n` and its `still` form. The waiting reminder counts only its own texts for that request, and state unreadable only its newest run (B-6). The ordinary stall counts every watchdog `LEAD-SILENT` newer than its progress, as in M6b, so an alarm from an outage with no progress since stands in for it. A reminder for one request never stands in for a decision's alarm (cold M6d R1-3).

**It starts a lead when all of these hold:**
1. **At the first alarm only:** this run posted the stall's first alarm: `stall_alarm` found none of the stall's own alarms newer than `since`, and posted one, its buzz sent or failed. The watchdog tries at most one start per stall, in that run, right after the alarm. So:
   - The alarm, posted before the fire, is the durable record of the attempt. A lost `LEAD-STARTED` can't lead to a second fire (qodo PR #14 finding 1).
   - A start held off, refused or failed at the first alarm is never retried. The alarm and reminders tell Matthew, and the architect decides.
   - The watchdog never starts a lead hours after its alarm, when the architect may be starting one (cold M6d R1-1).
   - A failed alarm post exits 1 before anything is fired, and the next run's alarm is then the first.
2. **One start per stall:** the room has no trusted `LEAD-STARTED` newer than `since` from anyone but a lead, confirmed or not. A lead's own handover start doesn't count: its successor is what stalled (cold M6d R1-5, qodo PR #14 finding 2).
3. **No sign of life since `since`:** a sign of life is either of these:
   - a trusted lead message of any kind newer than `since`, from a session that hasn't posted a `HANDOFF`. A session that handed over has ended, so its `HANDOFF`, its `LEAD-STARTED` and a `NEXT-LEAD-NEEDED` don't count, nor anything it posted before them;
   - the lease taken after `since`: it is held now, by a session that hasn't posted a `HANDOFF`, and the state branch's newest change to `lease_session` is newer than `since`. A session that handed over has ended even if its release failed, so its lease is no sign of life (cold M6d R3-4).

   So:
   - A lead that posted a `STATUS` after its progress, before a long builder run, is never taken over (cold M6d R2-1, R1-4).
   - A lead that joined after the stall began, even if all its posts failed, is never taken over.
4. **Not halted:** the machine block's status for this room isn't `paused`, `stopped` or `done`, whoever holds the lease. A lead that posted `PAUSED` or `STOPPED` and died before releasing the lease is not taken over: a takeover would set the status back to `running` (cold M6d R1-2).
5. **Configured:** the lead task is configured (`lead-task:` line and token).

**Starting:**
- When the rule holds, the watchdog runs `start-lead`'s logic as role `watchdog`: `--takeover` when the lease is held (a lead died silently after its progress, or a handover's release failed), plain otherwise. `start-lead` posts `LEAD-STARTED: <url> (<plain|takeover> join line, started by watchdog)`, or the unconfirmed form.
- `watchdog` comes back as a `start-lead` role, and `LEAD-STARTED` comes back into `WATCHDOG_CAN`.
- `start-lead`'s own guards still apply: room, status, lease, and the 30-minute "still starting" window. `--force` is never used.

**Outcomes:**

| `start-lead` | The watchdog |
| --- | --- |
| 0 (started, or unconfirmed with `LEAD-STARTED` posted) | Prints `started: …`. That is this stall's one start. |
| 1 (a definite failure, nothing posted) | Prints the error. No retry (rule 1): the alarm and its reminders tell Matthew. |
| 3 or 6 (refused, or not configured) | Prints a note. No retry: the alarm and its reminders tell Matthew. |

**Order of operations:** the alarm is posted before the start, in the same run, always, so a failed alarm post exits 1 before anything is fired. The `LEAD-STARTED` post keeps its retries and its de-duplication.

**`silent-after` and the 30-minute window:** a handover's `LEAD-STARTED` is about `silent-after` old at the first alarm. With `silent-after` under 45 minutes (a drill), `start-lead`'s "still starting" window can refuse the one start. The default is 3 hours, and drills use 60 minutes.

**The architect's starts and the watchdog's (cold M6d R1-1):** a stall's start can come from either, and an architect's starter task may run hours after it was created (finding U).
- The watchdog acts only in the run that posts the stall's first alarm (rule 1), and starts none after the architect's `LEAD-STARTED` (rule 2) or a sign of life (rule 3). So after the first alarm, every start is the architect's: if no watchdog `LEAD-STARTED` follows the first alarm within minutes, none will.
- **A plain start: `start-lead --seen ID`.** The architect's plain starter tasks (the lead after a `DECISION`, a resume, kickoff) pass the room's newest comment ID when the architect decided, or `0` when the room has no comments yet (kickoff, cold M6d R2-5). `start-lead` then refuses (exit 3) when the room has a trusted lead message, or a trusted `LEAD-STARTED` from any role, newer than comment ID: `refused: the room moved on after #ID: <kind> #<id> at <time>; read the room again`. So a starter that runs after the watchdog's start, or after a lead joined, starts nothing.
- **A takeover: `start-lead --takeover --replacing SESSION`.** A takeover replaces one lead: the session that held the lease when the architect decided (`state get lease_session`). `start-lead` refuses (exit 3) unless the lease is still held by SESSION: `refused: the lease is now <held by X | released>, not held by SESSION; read the room again`. So a late takeover starter starts nothing once that lead handed over, or the watchdog's or anyone's lead took the lease. It still starts while the lead it replaces keeps posting, which is the point of taking over a looping lead (cold M6d R3-1, which replaces R2-3's no-`--seen` exception). A takeover passes `--replacing`, not `--seen`.
- **Neither:** a lead's handover; the watchdog. `ARCHITECT.md` 8.4 passes one of them in every starter task.
- **A recovered lead:** `--replacing` refuses once the lease moved, not once the replaced lead made progress. A takeover starter runs about 10 minutes after the architect decided, so a lead silent for hours that recovers inside those minutes is the remaining window. A starter recreated after a late approval (finding U) is a new decision: the architect reads the room, the step and the mission branch again first, and recreates it only if the lead is still silent (cold M6d R4-1).
- **A halted build:** `start-lead --takeover` refuses, for any role, while this room's status is `paused` or `stopped`, because the takeover lead's `lease take --takeover` would set it back to `running`. On Matthew's word to resume, the architect adds `--force` (cold M6d R3-3, R2-2: the docs alone kept missing a path).

**Known limits:**
- **No retry:** a start that failed (an HTTP 5xx, say), was refused or wasn't configured at the first alarm isn't tried again. The architect starts the lead, as in M6b.
- **A lost `LEAD-STARTED`:** if the fire worked and all three posts failed, the room shows the alarm with no `LEAD-STARTED` after it. A lead's `LEAD ONLINE` follows if it started; the architect's starter task refuses once it does (`--seen`), or once it took the lease (`--replacing`).
- **Two runs at once:** the watchdog is one scheduled task, every 3 hours (hourly in drills), whose run takes about a minute, so its runs don't overlap. If two did (Matthew runs it by hand during a scheduled run), both could fire within the same seconds. The lease then lets one lead work: a plain lead finds the lease held and ends, and of two takeovers the first loses the lease and stops at its next write (qodo PR #14, finding 3).
- **A lead that dies after any post since its progress, or a successor that joined and died:** no automatic start (rule 3). The alarm and reminders come as in M6b, and the architect decides.
- **An alarm from another path standing in:** the ordinary stall counts an earlier state unreadable alarm newer than its progress as its own, and then posts no first alarm of its own, so it makes no start. The architect decides.

**What it means per path:**
- **An ordinary stall:**
  - With the lease released after a handover whose successor never came: one plain start after the first alarm.
  - With the lease held by a lead that made progress and posted nothing after it: one takeover.
  - If the started lead also dies before progress, it's the same stall: reminders, no second start.
- **A pending `DECISION`:**
  - If the architect started no lead, the watchdog starts one plain lead after its "no lead joined after DECISION-n" alarm, which comes `silent-after` after the decision.
  - If the architect's start failed, its `LEAD-STARTED` counts, and the watchdog only reminds.
  - If the started lead joins and dies at `waiting for owner`, that path only alarms.
- **Pre-start, a lead joined at `waiting for owner`, the waiting reminder, state unreadable:** alarms and reminders only.

The watchdog task's prompt doesn't change: room.py does the posting and starting. Its environment must be `agent-room`, because it needs the token.

## B-6: reminders while a room waits on Matthew

**Waiting-for-Matthew reminder:**
- **When it applies:**
  - the step starts with `waiting for owner`;
  - the lease is released (a parked lead);
  - room N is recorded as the current room, in `PLAYBOOK.md` or the machine block (a room nothing records gets no reminder, qodo PR #14, finding 6);
  - the room has a trusted lead request, an `ESCALATION-n` or `MERGE-HOLD-n`, with no trusted `DECISION-n` after it. The newest such open request is reminded about: an older one left open after a newer one was answered still gets its reminder (cold M6d R3-2), and a stale old request that a later decision made moot doesn't hide the one the lead parked on (cold M6d R4-2).
- **What it posts:** once `REMINDER_AFTER` × `silent-after` (12 hours by default) has passed since that request, `LEAD-SILENT: still waiting for Matthew: <KIND>-<n> since <time> (step <step>)`. It does this through `stall_alarm`, with `since` = the request's time and that text as both first and reminder, so it repeats every 12 hours under the same failed-buzz retry rules. Only its own reminders for that request count as this stall's alarms; a state unreadable alarm posted while it waited doesn't delay it (qodo PR #14, finding 5).
- **No start:** Matthew must decide.
- **Why:** this catches a request whose own buzz was lost (ntfy's limit, cold M6b R3-8 and S4-4), and an owner who forgot.

**State unreadable:** a `still state unreadable` reminder whose buzz failed is posted again at the next run, at most `BUZZ_RETRIES` times, like other reminders (cold M6b S4-2). Simplest is to route that alarm through `stall_alarm` too, keeping its texts. As before M6d, only the newest run of state unreadable alarms counts, the ones after the stall's last other alarm: an outage that comes back after an ordinary alarm gets a new first alarm (qodo PR #14, finding 4).

## Docs

- **`LEAD.md`:** the watchdog may start a lead only where none showed a sign of life since the stall began: any post after your progress, a `STATUS` before a long step included, keeps it from taking you over. So after every step change, and after starting builders (in the foreground or the background), the lead posts a `STATUS` (cold M6d R4-4).
- **`ARCHITECT.md`:**
  - **9.5:**
    - After a `LEAD-SILENT`, first read the status. If it is `paused` or `stopped`, start nothing except on Matthew's word to resume (9.4): a takeover sets the status back to `running` (cold M6d R2-2).
    - Then look for the watchdog's `LEAD-STARTED`. If there is one, wait for its `LEAD ONLINE` (about 30 minutes, the bullet on a recent `LEAD-STARTED`).
    - If there's none after the stall's first alarm, the watchdog won't start one: it tries only in that run. It held off (a sign of life since the stall began, a lead joined at `waiting for owner`, a halted build), was refused or not configured, or its fire failed. Decide by hand as now. A plain starter passes `--seen` and a takeover starter `--replacing`, so a lead whose `LEAD-STARTED` was lost but who joined isn't displaced.
    - A second stall alarm or a reminder after the watchdog's start means its lead failed too; the watchdog won't start another for that stall.
    - A lead that posted since its progress is never taken over by the watchdog: the architect decides, as in M6b.
    - Every takeover starter passes `--replacing <lease_session>`, a looping lead's included (cold M6d R3-1). The "lead task was deleted" bullet and any other path to a takeover go through step 3's status check, and `start-lead` refuses a takeover of a paused or stopped build anyway, except with `--force` on Matthew's word to resume (cold M6d R3-3).
  - **9.2:** if the architect doesn't start the lead after a decision, the watchdog does, `silent-after` later. The starter task passes `--seen`.
  - **8.4:** a plain starter task runs `start-lead N architect --seen <ID>`, with the room's newest comment ID when the architect decided, or `0` when the room has no comments yet (kickoff, cold M6d R2-5); a takeover starter runs `start-lead N architect --takeover --replacing <lease_session>`; a recreated starter keeps the same ID or session. Kickoff (section 8 and `docs/manual/kick-off-a-phase.md`): the watchdog alarms before the first lead joins, and starts leads only after one has joined (cold M6d R1-6, which also fixes the stale "alarms only" texts).
  - **9.5's cross-reference** to the 30-minute bullet points at the right bullet (cold M6d R1-7).
  - **9.1 table:** the waiting-for-Matthew reminder.
- **Manuals:** answer-a-buzz, message-kinds (the watchdog posts `LEAD-STARTED` again), troubleshooting, glossary, stop-or-pause (no watchdog start while paused or stopped, whoever holds the lease; no takeover by the architect either, except on Matthew's word to resume), kick-off-a-phase.
- **`docs/design/m6b-lead-relay.md`:** one note that M6d brings one watchdog start per stall back (B-5).
- **`BUILD-STATE.md`:** B-5 and B-6 done; A-12 states the principle.
- **`CHANGELOG.md`.**

## Tests

All offline, in `tests/test_relay.py` or a new `tests/test_m6d.py`.

**B-5:**
- A start after the alarm: a stall with the lease held by a lead that posted nothing since its progress (takeover), a handover whose successor never joined (plain), and a decision (plain).
- A handover at the same step (no progress), whose outgoing lead posted `STATUS`es before its `HANDOFF`: a start, as that session has ended.
- Alarms and reminders with no start: pre-start, and a lead that joined at `waiting for owner` and died, including a chain of such leads (cold M6d R2-4).
- No start without an alarm; a waiting reminder for another request doesn't stand in for a decision's alarm.
- No second start for the same stall: after a watchdog start, an architect start, an unconfirmed start, or a lead that joined with no `LEAD-STARTED` posted.
- No start after a sign of life since `since`: a `STATUS` one minute after the progress (cold M6d R2-1), a successor that joined and died, at that run and every later run; and the lease taken after `since` with no post at all.
- No start while the status is `paused` or `stopped` and the lease is still held.
- `start-lead --seen ID`: refused after a lead message or any `LEAD-STARTED` newer than ID (the watchdog's start, say); starts when nothing newer came; `--seen 0` in a room with no comments starts.
- `start-lead --takeover --replacing SESSION`: starts while SESSION holds the lease, even after its new posts; refused once the lease is released or held by another session.
- `start-lead --takeover` while paused or stopped with the lease held: refused for every role; starts with `--force`.
- An ended session's lease (it posted `HANDOFF`, its release failed) is no sign of life: a takeover at the first alarm.
- One try per stall: a definite failure, a refusal, a missing configuration or a hold-off at the first alarm is not retried at any later run, and a later run whose alarm is a reminder or a re-posted failed buzz fires nothing.
- A lost `LEAD-STARTED` (the fire worked, every post failed): no fire at the next run.
- Not configured (6) and refused (3) print a note only.
- A watchdog run never fires more than once.
- The alarm is posted before the fire; a failed alarm post means no fire.

**B-6:**
- The waiting reminder comes at 12 hours, repeats, and retries a failed buzz.
- No reminder once a `DECISION` came, or while the lease is held.
- An older request still open after a newer one was answered gets its reminder; with a stale older request and a newer open one, the newer one is named.
- No start on this path.
- The state-unreadable reminder retry, and a new first alarm for an outage that comes back after an ordinary alarm.
- A state unreadable alarm during the wait doesn't delay the waiting reminder.
- No reminder when no room is recorded.
