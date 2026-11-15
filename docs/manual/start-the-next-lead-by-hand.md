# Start the next lead by hand

[All manuals](README.md)

## When to use it

Normally you don't: each lead starts the next through the lead task, the watchdog starts a takeover lead, and the architect starts the lead after your decision. Start one yourself when the architect asks you to:

- After `NEXT-LEAD-NEEDED`, `PAUSED` or `STOPPED`, or to resume after an upgrade or an account move: the **normal join line**.
- When the old lead is gone without handing over, and no takeover lead joined: the **takeover line**. Only when the architect gives you one: after a `LEAD-SILENT` that no lead answered ([Answer a buzz](answer-a-buzz.md)).

## What you need first

- The architect chat in the project's Claude Project.
- The project's lead task ([Set up the lead task](set-up-the-lead-task.md)), for **Run now**. Without it, the Code tab works too.
- Claude usage left on the account you start the lead in.

## Steps

1. Ask the architect for the line, with the room number:
   - after `NEXT-LEAD-NEEDED`, `PAUSED` or `STOPPED`:

     ```text
     Give me the join line for room N.
     ```

   - when the old lead is gone, the architect offers the takeover line itself. If it didn't, ask:

     ```text
     Is the lead in room N gone? If so, give me the takeover line.
     ```

   The architect first checks that no lead is still alive: after a `LEAD-SILENT`, the watchdog has usually started a takeover lead already, and the architect gives it about 30 minutes to join. The takeover line ends with "Take over the lease … the previous lead stopped without handing over." The normal one doesn't.

   The architect may offer to start the lead itself through the lead task. Let it; approve the pop-up if one comes, and skip to "What you should see".
2. Takeover only: if the old lead's session is still open, archive it.
3. Start the lead through the lead task: open `https://claude.ai/code/routines`, open the task `agent-room lead SigorMatt/<repo>`, press **Run now**, and paste the line as its text.
4. Or, with no lead task, in the Code tab: start a new session, repository `SigorMatt/<repo>`, environment `agent-room`. Paste the line and send.
5. Never delete the lead task. Deleting a task deletes every session it started, the leads included.

## What you should see

- The lead's first line: "Operating as lead under agent-room `<version>`."
- `LEAD ONLINE` in the room within about 10 minutes. The lead picks up where the last one stopped. After `PAUSED` or `STOPPED`, it carries on, and doesn't act on the old `PAUSE` or `STOP` again.

## If you don't

- The lead says another lead holds the lease and ends (it "stands down"):
  - the old lead is gone (a `LEAD-SILENT` nobody answered): you used the normal line. Ask the architect for the takeover line and start again;
  - otherwise a lead is already running, for example a successor that did start. Nothing to do.
- The lead ends at once without a word: the line wasn't pasted whole. The lead task accepts only an exact join line. Copy it again from the architect.
- Two leads started by mistake: harmless. Only one takes over; the other ends without changing anything.
- Your Claude usage ran out: wait until it resets, or move the project ([Move a project to the other account](move-a-project-to-the-other-account.md)).
- **Run now** doesn't take the line, or the task is missing: use the Code tab (step 4), and tell the architect.
- No `LEAD ONLINE` after about 10 minutes: check the session's repository and environment, then tell the architect

  ```text
  check the room
  ```
