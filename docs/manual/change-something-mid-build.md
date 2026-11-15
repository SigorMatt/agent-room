# Change something mid-build

[All manuals](README.md)

## When to use it

You want to change the design or the plan while a phase runs: a feature, a criterion, the merge-hold list or the budget.

## What you need first

- The architect chat in the project's Claude Project.
- A choice: should the change apply **now**, to the running mission, or **from the next mission**?

## Steps

1. Send, filled in:

   ```text
   I want to change <what>. Apply it <now | from the next mission>.
   ```

2. The architect updates `DESIGN.md` (a new `D-n`) and `PLAYBOOK.md`, commits them, and posts `CHANGE-n` in the room, saying when it applies.
   - **Now:** the lead re-checks the running mission against the change and has the helpers build what changes.
   - **From the next mission:** the running mission finishes against the plan it started with.
3. Wait for the lead's `ACK CHANGE-n`.

## What you should see

- `CHANGE-n`, then `ACK CHANGE-n` in the room. The lead reads the room when it finishes its current step, so the ACK can take a while: one helper can run long. The architect tells you when to expect it.
- If the lead was waiting for your decision, no lead is running: the lead started after your decision reads the change and ACKs it.

## If you don't

- No ACK when the architect said to expect it: as for a decision ([Answer a buzz](answer-a-buzz.md), "If you don't").
