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

2. It posts `PAUSE` or `STOP` in the room. Neither gets an ACK: the buzz is the answer.
3. Wait for the `PAUSED` or `STOPPED` buzz. The lead has then saved its state, freed its place for the next lead, and ended.
4. To resume later, after a `PAUSE` or a `STOP`, start a lead with the normal join line, not the takeover line: [Start the next lead by hand](start-the-next-lead-by-hand.md).

## What you should see

- The buzz within about 30 minutes, the lead's next check-in. The message names the mission and step, and what is merged and pushed. After `STOP`, also anything the lead couldn't verify.
- The watchdog stays quiet while the build is paused or stopped.
- When you resume: `LEAD ONLINE`, and the new lead carries on from the saved step. It doesn't pause or stop again on the old message.

## If you don't

- No buzz after about 35 minutes: open the lead's session in the Code tab and send it

  ```text
  check the room
  ```

- After `STOP`, the lead lists something as unknown, such as a helper's unfinished work: nothing that wasn't pushed reaches GitHub, and the next lead starts from what was pushed.
