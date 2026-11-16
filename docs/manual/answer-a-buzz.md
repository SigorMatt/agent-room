# Answer a buzz

[All manuals](README.md)

## When to use it

Your phone buzzes with a title such as `ESCALATION-3 · pet-todo room 1`: the message kind, the project and the room number. Seven kinds buzz: `ESCALATION`, `MERGE-HOLD`, `NEXT-LEAD-NEEDED`, `PAUSED`, `STOPPED`, `DONE` and `LEAD-SILENT`. A `STATUS` buzzes only when the lead retries a failed `ESCALATION` or `MERGE-HOLD` buzz: that's a real request (below).

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
4. If the lead was waiting for you, it had ended. The architect starts a new lead to act on your decision, with a starter task: approve its pop-up when it appears (a late approval may need a second one). If no lead joins within three hours of your decision, a `LEAD-SILENT: no lead joined after DECISION-n` buzz follows (see `LEAD-SILENT` below), and if nobody started a lead, the watchdog then starts one.
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

### `STATUS`: a decision buzz that failed the first time

Its text reads `STATUS: the buzz for <KIND>-<n> failed (…): Matthew, a decision is needed in room N`. The lead posted an `ESCALATION` or `MERGE-HOLD` whose buzz didn't reach you, and is now waiting for you. Open the room, find that message, and answer it as its kind says above.

### `NEXT-LEAD-NEEDED`: start the next lead

A lead finished its part but couldn't start the next one through the lead task. The message says why. Nothing is lost.

1. The architect starts a lead with the normal join line, or gives it to you: [Start the next lead by hand](start-the-next-lead-by-hand.md).
2. Fix the cause too, or the next handover fails the same way:
   - `not configured` or `token rejected`: the lead task's token needs fixing ([Set up the lead task](set-up-the-lead-task.md), "If you don't").
   - `lead task … not found`: the task was deleted, or the playbook names an old one. The architect sets it up again with you and records its new ID ([Troubleshooting](troubleshooting.md), the new-task line).
   - `pin … isn't accepted by the lead task's prompt`: the playbook pins a pre-release. The architect pins a release, or `main`.

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

The watchdog saw nothing move. A lead died, got stuck or ran out of Claude usage, or the next one never started. Or a lead is alive but slow, or looping: posting without getting anywhere. After the alarm, the watchdog starts one lead itself, at most one per stall: a `LEAD-STARTED … started by watchdog` follows. It doesn't if a lead posted anything in the three hours before the alarm (a lead that posted a `STATUS` before a long step may still be working), if a lead was already started for this stall, or while the build is paused or stopped. The architect works out the rest, and starts a takeover lead if one is still needed.

Other texts:

- `LEAD-SILENT: no lead joined after DECISION-n`: no lead has joined in the three hours since your decision. The architect checks whether a lead was started; it starts one, or finds out with you why the start didn't take (often the lead task's token, or Claude usage), fixes it, and starts one.
- `LEAD-SILENT: still waiting for Matthew: <KIND>-n since <time> (…)`: an `ESCALATION` or `MERGE-HOLD` has waited 12 hours for your decision, maybe because its own buzz was lost. It repeats every 12 hours until you decide. Open the room, find that message, and answer it as its kind says above. Nothing starts on its own meanwhile.
- `LEAD-SILENT: no lead has joined room N in 12h`: the phase's first lead never joined. The watchdog doesn't start it. The architect checks the lead task with you (often its token), fixes it, and starts the first lead.
- `LEAD-SILENT: still no progress since …`, `still no lead joined after DECISION-n …`, `still state unreadable (…)` or `still no lead has joined room N`: a reminder, every 12 hours by default, while the stall or the wait lasts. Answer it like the first alarm.

1. If the buzz's message reads `LEAD-SILENT: state unreadable (…)`, the pipeline's records are broken, not the lead. The architect checks them first. If the `agent-room/state` branch was deleted, it is restored before any lead starts. Best: the architect pushes it again from its own copy, or you push it from a fork or a local clone that still has it. In a local clone, run:

   ```bash
   git push origin agent-room/state
   ```

   Only if no copy exists does the architect recreate it from scratch, and tell the next lead to rebuild its records from the merged pull requests and the room. Then go on.
2. The architect tells you where the build stopped, whether the lead is dead or alive, and whether the watchdog already started a lead for this stall. If a lead was started less than 30 minutes ago and hasn't joined yet, it waits until then, so it doesn't start a second lead while the first is still starting. It checks back itself, or asks you to send it this then:

   ```text
   check the room
   ```

3. If a lead is alive and working (it posted a `STATUS` lately, say), you need no new lead: the architect tells you where it is. If it's looping, posting without progress, the architect asks you before taking over.
4. If the lead is dead, a takeover lead is started, in exactly one of these two ways, never both:
   - **The architect starts it** with a starter task: approve its pop-up when it appears (a late approval may need a second one). A `LEAD-STARTED` follows about 10 minutes later. That's all: don't start a lead yourself.
   - **Or, if it can't, it posts `LEAD-STARTED: by hand …` and gives you the takeover line.** Start the lead soon after. The line ends with "Take over the lease … the previous lead stopped without handing over." Start a lead with it ([Start the next lead by hand](start-the-next-lead-by-hand.md)), then send the architect the new session's link, so it posts `LEAD-STARTED`. Use a takeover line only when the architect gives you one.

   If the watchdog starts a lead first, the architect's starter task finds it and starts nothing (its run says `refused: the room moved on after #…`), so you never get two. Either way, if the old lead's session is still open, archive it. If the new lead stalls too, the next alarm or reminder brings you back here; the watchdog doesn't start a second lead for the same stall.

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
  - Otherwise a lead is running, maybe busy with a helper. The architect checks again about an hour after that lead started. If there's still no ACK and no lead message, the lead may have stopped. The watchdog notices, even while the step says it waits for you: a `LEAD-SILENT` buzz follows within three hours of the lead's `LEAD ONLINE`. Answer it as above: the architect starts the takeover.
- Tapping the buzz didn't open the room: in GitHub, open the repo, then **Issues**, and filter by the label `agent-room`.
- Something else: [Troubleshooting](troubleshooting.md).
