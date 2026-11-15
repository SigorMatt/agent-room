# Steer from GitHub

[All manuals](README.md)

## When to use it

To pause or stop the build straight from GitHub, when the architect chat isn't handy. A comment you post yourself in the room outranks both agents.

## What you need first

- The room: the issue labelled `agent-room` in the repo. A buzz opens it, or use **Issues** filtered by that label.
- GitHub, signed in as `SigorMatt`. Only your login's comments count; anyone else's are ignored.

## Steps

1. Open the room and add a comment that starts with the kind, followed by your reason:

   ```text
   PAUSE: <why>
   ```

   or

   ```text
   STOP: <why>
   ```

   `PAUSE` lets running work finish and saves it. `STOP` halts now ([STOP or PAUSE](stop-or-pause.md)).
2. For a decision or a design change, use the architect instead, so it lands in `DESIGN.md` ([Answer a buzz](answer-a-buzz.md), [Change something mid-build](change-something-mid-build.md)).
3. Never put secrets or your ntfy topic in a comment. On a public repo, anyone can read the room.

## What you should see

- The lead sees your comment at its next check-in, within about 30 minutes, and answers with a `PAUSED` or `STOPPED` buzz. Neither gets an ACK.

## If you don't

- No buzz after about 35 minutes: open the lead's session in the Code tab and send it `check the room`.
- A handover was under way (the last lead message is `HANDOFF`): the next lead reads your comment when it joins.
