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

2. The architect opens the room (a GitHub issue labelled `agent-room`), creates the watchdog (a scheduled task that buzzes you if no lead makes progress for three hours), and runs preflight.
   - Fix whatever it asks ([Fix preflight](fix-preflight.md)). If it asks you to turn on "Automatically delete head branches", see [Create the repo](create-the-repo.md), step 3.
   - If it says the watchdog's runs will ask for approval: open the scheduled task named `agent-room watchdog SigorMatt/<repo> room N` in the Claude app, and switch on **Automatically approve**.
3. It asks whether the `agent-room` environment has `ROOM_NTFY_TOPIC`, `QODO_REVIEW`, and the playbook's websites and secrets. Say yes only when they're all there.
4. It gives you the join line, starting `Join agent room N in SigorMatt/<repo> as lead`. Copy it whole.
5. In the Claude app, open the **Code** tab and start a new session: repository `SigorMatt/<repo>`, environment `agent-room`. Paste the join line and send.
6. Put the phone away. Only seven kinds of message buzz you ([Message kinds](message-kinds.md)).

## What you should see

- The lead's first line: "Operating as lead under agent-room `<version>`."
- In the room on GitHub, within about 10 minutes: `LEAD ONLINE`, then `PLAN` with the phase's missions. Neither buzzes.
- Later, `STATUS` lines as work finishes. Each mission ends as one merged pull request.

## If you don't

- No `LEAD ONLINE` after about 10 minutes: check the session's repository and environment, then tell the architect

  ```text
  check the room
  ```

- The lead escalates a preflight `✗`: [Fix preflight](fix-preflight.md).
- No first line in the lead session: the join line wasn't pasted whole, or agent-room is private.
