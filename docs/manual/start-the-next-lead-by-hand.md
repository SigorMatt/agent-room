# Start the next lead by hand

[All manuals](README.md)

## When to use it

- After `NEXT-LEAD-NEEDED`, `PAUSED` or `STOPPED`, or to resume after an upgrade or an account move: the **normal join line**.
- When the old lead is gone without handing over: the **takeover line**. Only when the architect gives you one: after a `LEAD-SILENT` that no lead answered, or when a lead waiting for your decision doesn't answer `check the room` ([Answer a buzz](answer-a-buzz.md)).

## What you need first

- The architect chat in the project's Claude Project.
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

   The architect first checks that no lead is still alive: after a `LEAD-SILENT` it may wait up to about 35 minutes for the lead's check-in. The takeover line ends with "Take over the lease … the previous lead stopped without handing over." The normal one doesn't.
2. Takeover only: if the old lead's session is still open in the Code tab, archive it.
3. In the Code tab, start a new session: repository `SigorMatt/<repo>`, environment `agent-room`. Paste the line and send.
4. Never delete a scheduled task a lead created. Deleting it deletes the session it started. Those tasks switch themselves off after running.

## What you should see

- The lead's first line: "Operating as lead under agent-room `<version>`."
- `LEAD ONLINE` in the room within about 10 minutes. The lead picks up where the last one stopped. After `PAUSED` or `STOPPED`, it carries on, and doesn't act on the old `PAUSE` or `STOP` again.

## If you don't

- The lead says another lead holds the lease and ends (it "stands down"):
  - the old lead is gone (a `LEAD-SILENT` nobody answered, or a waiting lead that didn't answer): you used the normal line. Ask the architect for the takeover line and start again;
  - otherwise a lead is already running, for example a successor that did start. Nothing to do.
- Two leads started by mistake: harmless. Only one takes over; the other ends without changing anything.
- Your Claude usage ran out: wait until it resets, or move the project ([Move a project to the other account](move-a-project-to-the-other-account.md)).
- No `LEAD ONLINE` after about 10 minutes: check the session's repository and environment, then tell the architect `check the room`.
