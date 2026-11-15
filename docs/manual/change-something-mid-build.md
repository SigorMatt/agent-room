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

- `CHANGE-n`, then `ACK CHANGE-n` in the room. The lead checks the room about every 30 minutes, so the ACK can take that long. The architect tells you when to expect it.

## If you don't

- No ACK after about 35 minutes: as for a decision ([Answer a buzz](answer-a-buzz.md), "If you don't").
