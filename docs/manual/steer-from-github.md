# Steer from GitHub

[All manuals](README.md)

## When to use it

To pause or stop the build, or to give the lead an instruction, straight from GitHub, when the architect chat isn't handy. A comment you post yourself in the room outranks both agents.

## What you need first

- The room: the issue labelled `agent-room` in the repo. A buzz opens it, or use **Issues** filtered by that label.
- GitHub, signed in as `SigorMatt`. Only your login's comments count; anyone else's are ignored.

## Steps

1. Open the room and add a comment.
   - **To pause or stop,** start it with the kind, followed by your reason:

     ```text
     PAUSE: <why>
     ```

     or

     ```text
     STOP: <why>
     ```

     `PAUSE` lets running work finish and saves it. `STOP` halts now ([STOP or PAUSE](stop-or-pause.md)).
   - **For anything else,** write the instruction in your own words, for example:

     ```text
     Do the CSV export task before the search task.
     ```

     The lead treats it as your instruction. If it stays within the design and the playbook, the lead follows it. If it doesn't, the lead posts an `ESCALATION` that quotes your comment, and you decide with the architect ([Answer a buzz](answer-a-buzz.md)).
2. For a decision or a design change, use the architect instead, so it lands in `DESIGN.md` ([Answer a buzz](answer-a-buzz.md), [Change something mid-build](change-something-mid-build.md)).
3. Never put secrets or your ntfy topic in a comment. On a public repo, anyone can read the room.

## What you should see

The lead sees your comment when it finishes its current step (one helper can take a while), and answers:

- `PAUSE` or `STOP`: a `PAUSED` or `STOPPED` buzz. Neither gets an ACK.
- An instruction it follows: a `STATUS` in the room saying what it did. A `STATUS` doesn't buzz.
- An instruction outside the design: an `ESCALATION` buzz quoting your comment.

## If you don't

- No answer after about 30 minutes: send the architect

  ```text
  check the room
  ```

  It tells you where the lead is.
- A handover was under way (the last lead message is `HANDOFF`): the next lead reads your comment when it joins.
- The lead was waiting for your decision: it had ended, so no lead is running to read your comment. Ask the architect to start one ([Start the next lead by hand](start-the-next-lead-by-hand.md)).
