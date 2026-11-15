# Wrap up an architect session

[All manuals](README.md)

## When to use it

At the end of each design session, and before you start a fresh architect chat. Each design session or phase gets a fresh chat, and this note carries the thread across.

## What you need first

- The architect chat you've been using.

## Steps

1. Send:

   ```text
   wrap up the session
   ```

2. The architect rewrites `HANDOFF.md`: what the session covered, the open threads, what was being explored, and which way you leaned. It commits it and tells you.
3. Next time, start a new chat in the project's Claude Project. It reads the note first.

## What you should see

- The architect says the handoff note is committed.
- `docs/playbook/HANDOFF.md` on the `agent-room/state` branch has today's date ([Read the design and state on the state branch](read-the-state-branch.md)).

## If you don't

- It reports an error committing: send `wrap up the session` again.
- The new chat doesn't mention the note: ask it `What does HANDOFF.md say?`
