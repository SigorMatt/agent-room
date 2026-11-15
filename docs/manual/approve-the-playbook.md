# Approve the playbook

[All manuals](README.md)

## When to use it

Before every kickoff, when the architect has drafted `PLAYBOOK.md` and walks you through it. It commits only what you approve.

## What you need first

- A design session in the architect chat.
- Optionally, the draft open on GitHub:

  ```text
  https://github.com/SigorMatt/<repo>/blob/agent-room/state/docs/playbook/PLAYBOOK.md
  ```

## Steps

1. If the walk-through hasn't started, send:

   ```text
   Walk me through the playbook: items and criteria, the test command, the merge-hold list, environment needs, the lead's discretion and the mission budget.
   ```

2. Check each part:
   - **Items and criteria:** each criterion names the check that proves it, and a cloud machine can run it (no GPU, no lab network, no local models). Anything else is marked "(manual check for Matthew)".
   - **Test command:** the `test:` line runs every test.
   - **Merge-hold list:** the areas where you approve every merge yourself ([Merge-hold list](merge-hold-list.md)).
   - **Environment needs:** every website to allow and every secret to add.
   - **Lead's discretion:** what the lead decides without asking you. The more you settle here, the fewer buzzes.
   - **Mission budget:** hours per mission before the lead must ask you. 8 by default.
3. Ask for changes in plain words. When it's right, send:

   ```text
   Approved. Commit the playbook.
   ```

## What you should see

- The architect confirms the commit.
- The file on the state branch matches what you approved.

## If you don't

- A criterion needs something a cloud machine lacks: ask the architect to mock it or mark it a manual check.
- The commit clashed with another write: the architect re-applies its edits and commits again by itself. Wait for its confirmation.
