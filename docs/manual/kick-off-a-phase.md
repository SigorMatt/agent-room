# Kick off a phase and start its first lead

[All manuals](README.md)

## When to use it

When a phase's playbook is approved and its environment needs are set. For the first phase and every later one.

## What you need first

- The approved playbook ([Approve the playbook](approve-the-playbook.md)) and the environment needs done ([Set up environment needs](set-up-environment-needs.md)).
- The architect chat of this design session.

## Steps

1. Send, with the phase number:

   ```text
   Kick off phase <p>.
   ```

2. The architect opens the room (a GitHub issue labelled `agent-room`), creates the watchdog (a scheduled task that only buzzes you: when no lead makes progress for three hours, or none joins after your decision, with a reminder every 12 hours), and runs preflight.
   - Fix whatever it asks ([Fix preflight](fix-preflight.md)). If it asks you to turn on "Automatically delete head branches", see [Create the repo](create-the-repo.md), step 3.
   - If it says the watchdog's runs will ask for approval: open the scheduled task named `agent-room watchdog SigorMatt/<repo> room N` in the Claude app, and switch on **Automatically approve**.
3. At a project's first kickoff only, it asks you to set up the lead task, and gives you the task's prompt. Do it on a computer: [Set up the lead task](set-up-the-lead-task.md). Later phases reuse the task.
4. It asks whether the `agent-room` environment has `ROOM_NTFY_TOPIC`, `QODO_REVIEW`, the lead task's token, and the playbook's websites and secrets. Say yes only when they're all there.
5. It starts the first lead itself: it creates a one-time starter task, which starts the lead through the lead task about two minutes later. Approve the pop-up for that task. If it can't start the lead, it gives you the join line, starting `Join agent room N in SigorMatt/<repo> as lead`: start the lead with that ([Start the next lead by hand](start-the-next-lead-by-hand.md)).
6. Put the phone away. Only seven kinds of message buzz you ([Message kinds](message-kinds.md)). From now on, each lead starts the next.

## What you should see

- In the room on GitHub: `LEAD-STARTED` with a link to the lead's session, then within about 10 minutes `LEAD ONLINE`, then `PLAN` with the phase's missions. None of them buzzes.
- In the lead's session, its first line: "Operating as lead under agent-room `<version>`."
- Later, `STATUS` lines as work finishes. Each mission ends as one merged pull request.

## If you don't

- No `LEAD ONLINE` after about 15 minutes: tell the architect

  ```text
  check the room
  ```

- The architect shows `! lead task not configured`: do step 3.
- The lead escalates a preflight `✗`: [Fix preflight](fix-preflight.md).
- No first line in a lead session you started: the join line wasn't pasted whole, or agent-room is private.
