# Answer a buzz

[All manuals](README.md)

## When to use it

Your phone buzzes with a title such as `ESCALATION-3 · pet-todo room 1`: the message kind, the project and the room number. Seven kinds buzz: `ESCALATION`, `MERGE-HOLD`, `NEXT-LEAD-NEEDED`, `PAUSED`, `STOPPED`, `DONE` and `LEAD-SILENT`.

## What you need first

- The ntfy app, GitHub and the Claude app.
- The project's Claude Project. Use this phase's architect chat, or start a new chat there: it reads the design and the room by itself.

## Steps

1. Tap the buzz. It opens the room on GitHub, at the message or at the top. Read it if you like.
2. Open the architect chat in the project's Claude Project and send:

   ```text
   check the room
   ```

3. The architect explains the message in plain terms. Then follow its kind below.

### `ESCALATION-n`: the lead needs a decision

The design doesn't settle a question. Meanwhile the lead keeps building whatever isn't blocked.

1. The architect explains the question, the options, the lead's recommendation, and what is blocked.
2. Decide together. Ask anything you need.
3. The architect records your decision in `DESIGN.md`, then posts `DECISION-n` in the room, saying how the mission continues.
4. If the lead was waiting for you, it had ended. The architect starts a new lead to act on your decision. You may get an approval pop-up: approve it.
5. Wait for the lead's `ACK DECISION-n` ("What you should see").

If the escalation is a **pipeline fault** (the quoted line says "the records can't fix this"), agent-room itself needs a fix. Report it ([Report a pipeline problem](report-a-pipeline-problem.md)); the mission waits. When the patched release is out, tell the architect, with its version:

```text
Bump the pin to <version>. It's a patch release for the pipeline fault.
```

It bumps the pin, posts a `DECISION-n` telling the lead to re-download and run the gate again, and starts that lead.

### `MERGE-HOLD-n`: a pull request is ready but held

The message reads `MERGE-HOLD-n: PR #<number>, reason <r> (…)`. One hold can name several reasons, as `reason 1, reason 5`; your decision covers each. The reasons are on [Merge-hold list](merge-hold-list.md).

1. The architect explains the reason. Open the pull request on GitHub if you want to look.
2. Choose how the mission continues:
   - **merge as is,** except for reason 3: failing checks would fail the gate again;
   - for reason 3 only, **fix or relax the check** yourself, for example a flaky test or a check that no longer fits; the lead then runs the gate again;
   - **back to Build** with an extra budget: by default one more cold-review round and up to two Qodo rounds. The mission's hours budget starts again from your decision;
   - **drop the mission and re-plan.**
3. The architect records it, posts `DECISION-n` and starts a new lead, as for an escalation. Wait for the ACK.

### `NEXT-LEAD-NEEDED`: start the next lead

A lead finished its part but couldn't start the next one through the lead task. The message says why. Nothing is lost.

1. The architect starts a lead with the normal join line, or gives it to you: [Start the next lead by hand](start-the-next-lead-by-hand.md).
2. If the reason says `not configured` or `token rejected`, the lead task's token needs fixing, or the next handover fails too: [Set up the lead task](set-up-the-lead-task.md), "If you don't".

### `PAUSED`: paused, as asked

The lead let running work finish, saved everything and ended. Nothing runs now. To resume, ask the architect to start a lead ([STOP or PAUSE](stop-or-pause.md), step 4).

### `STOPPED`: halted, as asked

The lead stopped its helpers, recorded what it verified and what it couldn't, and ended. Go through that with the architect. To resume, ask the architect to start a lead ([STOP or PAUSE](stop-or-pause.md), step 4).

### `DONE`: the phase is complete

The lead merged the last mission, checked every criterion, posted `DONE`, closed the room and ended.

1. The architect checks every item's criteria and deletes the watchdog task; a lead can't. The lead task stays, for the next phase.
2. Then either plan more ([Start a new phase](start-a-new-phase.md)) or finish ([Wrap up an architect session](wrap-up-an-architect-session.md)).
3. Optional: on `https://github.com/SigorMatt/<repo>/branches`, delete leftover `mission/…` branches whose pull request is merged, with the bin icon. Never delete `main` or `agent-room/state`.

### `LEAD-SILENT`: no progress for three hours

The watchdog saw nothing move. A lead died, got stuck or ran out of Claude usage, or the next one never started. With the lead task set up, the watchdog has already started a takeover lead: a `LEAD-STARTED` follows in the room, then that lead's `LEAD ONLINE`. It tries at most two takeovers for the same stall.

1. If the buzz's message reads `LEAD-SILENT: state unreadable (…)`, the pipeline's records are broken, not the lead. The architect checks them first. If the `agent-room/state` branch was deleted, it is restored before any lead starts. Best: the architect pushes it again from its own copy, or you push it from a fork or a local clone that still has it. In a local clone, run:

   ```bash
   git push origin agent-room/state
   ```

   Only if no copy exists does the architect recreate it from scratch, and tell the next lead to rebuild its records from the merged pull requests and the room. The watchdog starts no lead after this alarm. Then go on.
2. The architect tells you where the build stopped. Then it checks that the takeover lead's `LEAD ONLINE` comes, within about 15 minutes of the alarm. It checks back itself, or asks you to send it this then:

   ```text
   check the room
   ```

3. If a `LEAD ONLINE` came after the alarm, a takeover lead joined: the architect tells you where it is, and you need no new lead for now. If that lead makes no progress either, a second `LEAD-SILENT` follows ("the lead started at … made no progress") with one more takeover, the watchdog's last try. Answer that buzz too: the architect checks later that this lead moves, and if it doesn't, looks into why leads keep failing before anyone starts another.
4. If no takeover lead came online, the architect starts a takeover lead itself, or gives you the **takeover line**. It ends with "Take over the lease … the previous lead stopped without handing over."
5. If the old lead's session is still open, archive it.
6. Start a lead with the takeover line: [Start the next lead by hand](start-the-next-lead-by-hand.md). Use a takeover line only when the architect gives you one.

## What you should see

- After a `DECISION-n`: `LEAD-STARTED`, then `LEAD ONLINE` and `ACK DECISION-n` in the room, usually within 15 minutes. If the lead was still working rather than waiting for you, it sees the decision when its current step ends, which can take longer. The architect tells you when to expect it and checks back itself, or asks you to send it this then:

  ```text
  check for the ACK
  ```

- After a lead starts another: `LEAD-STARTED`, then `LEAD ONLINE`. Neither buzzes.
- After you start a lead: `LEAD ONLINE` in the room within about 10 minutes.
- After `DONE`: the room closed, and the architect deleted the watchdog task.

## If you don't

- No ACK when the architect said to expect it: send the architect

  ```text
  check for the ACK
  ```

  - If the last lead message is `HANDOFF` with no `LEAD ONLINE` after it, the next lead never started. The architect starts one, or gives you the normal join line: [Start the next lead by hand](start-the-next-lead-by-hand.md).
  - If no lead started after your decision, or one started but didn't come online, the architect starts one. If the lead that waited for you died before it ended properly, that takes the takeover line.
  - Otherwise a lead is running, maybe busy with a helper. The architect checks again about an hour after that lead started. If there's still no ACK and no lead message, the lead may have stopped. The watchdog notices, even while the step says it waits for you: a `LEAD-SILENT` buzz follows within three hours of the lead's `LEAD ONLINE`, with a takeover lead. Answer it as above.
- Tapping the buzz didn't open the room: in GitHub, open the repo, then **Issues**, and filter by the label `agent-room`.
- Something else: [Troubleshooting](troubleshooting.md).
