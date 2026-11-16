# STOP or PAUSE

[All manuals](README.md)

## When to use it

- **PAUSE:** you want the build to rest: for an upgrade, a move to your other account, or a break from buzzes. Running work finishes and is saved.
- **STOP:** something is going wrong and you want it halted now.

## What you need first

- The architect chat in the project's Claude Project. Or the room on GitHub ([Steer from GitHub](steer-from-github.md)).

## Steps

1. Tell the architect, filled in:

   ```text
   Pause the lead: <why>.
   ```

   or

   ```text
   Stop the lead: <why>.
   ```

2. It posts `PAUSE` or `STOP` in the room. Neither gets an ACK: the buzz is the answer. If the lead was waiting for your decision, no lead is running, so the architect starts one to answer. Approve the pop-up if one comes.
3. Wait for the `PAUSED` or `STOPPED` buzz. The lead has then saved its state, freed its place for the next lead, and ended.
4. To resume later, after a `PAUSE` or a `STOP`, tell the architect, with the room number:

   ```text
   Resume the lead in room N.
   ```

   It starts a lead with a starter task, with the normal join line, not the takeover line. Approve the task's pop-up. Only the architect resumes: no lead starts another while the build is paused or stopped, the watchdog starts none either, even if the old lead still holds the lease, and the architect starts no takeover either until you say to resume. agent-room refuses such a takeover anyway; on your word to resume, the architect overrides that. If it can't, it gives you the line: [Start the next lead by hand](start-the-next-lead-by-hand.md).

## What you should see

- The buzz when the lead finishes its current step; one helper can take a while. The message names the mission and step, and what is merged and pushed. After `STOP`, also anything the lead couldn't verify.
- The watchdog stays quiet while the build is paused or stopped, and never starts a lead then, whoever holds the lease.
- When you resume: `LEAD-STARTED`, then `LEAD ONLINE`, and the new lead carries on from the saved step. It doesn't pause or stop again on the old message.

## If you don't

- No buzz after about 30 minutes: send the architect

  ```text
  check the room
  ```

  It tells you where the lead is. If the lead is stuck, the watchdog's `LEAD-SILENT` follows, and a takeover lead handles your `PAUSE` or `STOP` first. The watchdog starts it at that alarm if the lead posted nothing since its last progress; otherwise the architect does.
- After `STOP`, the lead lists something as unknown, such as a helper's unfinished work: nothing that wasn't pushed reaches GitHub, and the next lead starts from what was pushed.
