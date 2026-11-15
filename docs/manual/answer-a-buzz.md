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
4. Wait for the lead's `ACK DECISION-n` ("What you should see").

If the escalation is a **pipeline fault** (the quoted line says "the records can't fix this"), agent-room itself needs a fix. Report it ([Report a pipeline problem](report-a-pipeline-problem.md)); the mission waits. When the patched release is out, tell the architect, with its version:

```text
Bump the pin to <version>. It's a patch release for the pipeline fault.
```

It bumps the pin and posts a `DECISION-n` telling the lead to re-download and run the gate again.

### `MERGE-HOLD-n`: a pull request is ready but held

The message reads `MERGE-HOLD-n: PR #<number>, reason <r> (…)`. One hold can name several reasons, as `reason 1, reason 5`; your decision covers each. The reasons are on [Merge-hold list](merge-hold-list.md).

1. The architect explains the reason. Open the pull request on GitHub if you want to look.
2. Choose how the mission continues:
   - **merge as is,** except for reason 3: failing checks would fail the gate again;
   - for reason 3 only, **fix or relax the check** yourself, for example a flaky test or a check that no longer fits; the lead then runs the gate again;
   - **back to Build** with an extra budget: by default one more cold-review round and up to two Qodo rounds. The mission's hours budget starts again from your decision;
   - **drop the mission and re-plan.**
3. The architect records it and posts `DECISION-n`. Wait for the ACK.

### `NEXT-LEAD-NEEDED`: start the next lead

A lead finished its part but couldn't schedule the next one. Nothing is lost. Start one with the normal join line: [Start the next lead by hand](start-the-next-lead-by-hand.md).

### `PAUSED`: paused, as asked

The lead let running work finish, saved everything and ended. Nothing runs now. To resume, start a lead with the normal join line: [Start the next lead by hand](start-the-next-lead-by-hand.md).

### `STOPPED`: halted, as asked

The lead stopped its helpers, recorded what it verified and what it couldn't, and ended. Go through that with the architect. To resume, start a lead with the normal join line: [Start the next lead by hand](start-the-next-lead-by-hand.md).

### `DONE`: the phase is complete

The lead merged the last mission, checked every criterion, posted `DONE` and closed the room. Then it deleted the watchdog task and ended.

1. The architect checks every item's criteria. If the watchdog task is still there (the lead stopped before deleting it), the architect deletes it.
2. Then either plan more ([Start a new phase](start-a-new-phase.md)) or finish ([Wrap up an architect session](wrap-up-an-architect-session.md)).
3. Optional: on `https://github.com/SigorMatt/<repo>/branches`, delete leftover `mission/…` branches whose pull request is merged, with the bin icon. Never delete `main` or `agent-room/state`.

### `LEAD-SILENT`: no progress for three hours

The watchdog saw nothing move. A lead died, got stuck or ran out of Claude usage, or the next one never started. Or the lead is alive but slow: it sees the alarm at its next check-in, within about 30 minutes, and answers in the room.

1. If the buzz's message reads `LEAD-SILENT: state unreadable (…)`, the pipeline's records are broken, not the lead. The architect checks them first. If the `agent-room/state` branch was deleted, it is restored before any lead starts. Best: the architect pushes it again from its own copy, or you push it from a fork or a local clone that still has it. In a local clone, run:

   ```bash
   git push origin agent-room/state
   ```

   Only if no copy exists does the architect recreate it from scratch, and tell the next lead to rebuild its records from the merged pull requests and the room. Then go on.
2. The architect tells you where the build stopped. Then it waits for the lead's next check-in, until about 35 minutes after the alarm. It checks back itself, or asks you to send it this then:

   ```text
   check the room
   ```

3. If any lead message came after the alarm, the lead is alive: the architect tells you where it is, and you need no new lead. Stop here. If the lead posted or pushed work within the last hour, it may be busy with a helper and unable to check in yet: the architect waits one more check-in, about 35 minutes.
4. Otherwise it gives you the **takeover line**. It ends with "Take over the lease … the previous lead stopped without handing over."
5. If the old lead's session is still open in the Code tab, archive it.
6. Start a lead with the takeover line: [Start the next lead by hand](start-the-next-lead-by-hand.md). Use a takeover line only when the architect gives you one.

## What you should see

- After a `DECISION-n`: `ACK DECISION-n` in the room. The lead checks the room about every 30 minutes, so the ACK can take that long. The architect tells you when to expect it (about 35 minutes) and checks back itself, or asks you to send it this then:

  ```text
  check for the ACK
  ```

- After you start a lead: `LEAD ONLINE` in the room within about 10 minutes.
- After `DONE`: the room closed, and no watchdog task left.

## If you don't

- No ACK after about 35 minutes: send the architect

  ```text
  check for the ACK
  ```

  - If the last lead message is `HANDOFF` with no `LEAD ONLINE` after it, the next lead never started. The architect gives you the normal join line: [Start the next lead by hand](start-the-next-lead-by-hand.md).
  - Otherwise, open the lead's session in the Code tab and send it

    ```text
    check the room
    ```

  - Still no answer about 35 minutes later, or the session is gone: send the architect again

    ```text
    check for the ACK
    ```

    If the lead was waiting for your decision, the watchdog stays quiet, so the architect treats the lead as dead and gives you the takeover line. Archive the old session if it's open, then start a lead with that line.
- Tapping the buzz didn't open the room: in GitHub, open the repo, then **Issues**, and filter by the label `agent-room`.
- Something else: [Troubleshooting](troubleshooting.md).
