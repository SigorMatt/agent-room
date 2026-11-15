# Start a new phase

[All manuals](README.md)

## When to use it

After the `DONE` buzz, when you want the project to do more. The playbook gets a new phase, with a new room.

## What you need first

- The previous phase's `DONE`.
- Its architect session wrapped up ([Wrap up an architect session](wrap-up-an-architect-session.md)).

## Steps

1. Start a new chat in the project's Claude Project (a fresh chat for each phase) and send, filled in:

   ```text
   Let's plan phase <p>: <what it should add>.
   ```

2. Design with it. It adds the phase and its items to `PLAYBOOK.md`. Findings that earlier reviews put off to this phase are planned in by the first lead, without you.
3. [Approve the playbook](approve-the-playbook.md), and [Set up environment needs](set-up-environment-needs.md) if new ones appear.
4. [Kick off a phase and start its first lead](kick-off-a-phase.md): a new room, a new watchdog, and a join line.

## What you should see

- A new room (a new issue labelled `agent-room`).
- `LEAD ONLINE`, then `PLAN` listing the new phase's missions.

## If you don't

- Kickoff problems: [Kick off a phase and start its first lead](kick-off-a-phase.md), "If you don't".
- The old room is still open: the last phase didn't finish. Ask the architect `check the room` for the old room's number.
