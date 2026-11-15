# Start the next lead by hand

[All manuals](README.md)

## When to use it

- After `NEXT-LEAD-NEEDED`, `PAUSED` or `STOPPED`, or to resume after an upgrade or an account move: the **normal join line**.
- After `LEAD-SILENT`: the **takeover line**. Only then.

## What you need first

- The architect chat in the project's Claude Project.
- Claude usage left on the account you start the lead in.

## Steps

1. Ask the architect for the line, with the room number:
   - after `NEXT-LEAD-NEEDED`, `PAUSED` or `STOPPED`:

     ```text
     Give me the join line for room N.
     ```

   - after `LEAD-SILENT`:

     ```text
     Give me the takeover line for room N.
     ```

   The takeover line ends with "Take over the lease … the previous lead stopped without handing over." The normal one doesn't.
2. Takeover only: if the old lead's session is still open in the Code tab, archive it.
3. In the Code tab, start a new session: repository `SigorMatt/<repo>`, environment `agent-room`. Paste the line and send.
4. Never delete a scheduled task a lead created. Deleting it deletes the session it started. Those tasks switch themselves off after running.

## What you should see

- The lead's first line: "Operating as lead under agent-room `<version>`."
- `LEAD ONLINE` in the room within about 10 minutes. The lead picks up where the last one stopped.

## If you don't

- The lead says another lead holds the lease and ends (it "stands down"):
  - after a `LEAD-SILENT`: you used the normal line. Ask for the takeover line and start again;
  - otherwise a lead is already running, for example a successor that did start. Nothing to do.
- Two leads started by mistake: harmless. Only one takes over; the other ends without changing anything.
- Your Claude usage ran out: wait until it resets, or move the project ([Move a project to the other account](move-a-project-to-the-other-account.md)).
- No `LEAD ONLINE` after about 10 minutes: check the session's repository and environment, then tell the architect `check the room`.
