# Read the design and state on the state branch

[All manuals](README.md)

## When to use it

To see the design, the plan or where the build stands, without asking anyone.

## What you need first

- The GitHub app or a browser.

## Steps

1. Open this, filled in. In the GitHub app: the repo, then the branch picker, `agent-room/state`, then `docs/playbook`.

   ```text
   https://github.com/SigorMatt/<repo>/tree/agent-room/state/docs/playbook
   ```

2. Pick a file:

   | File | Shows |
   | --- | --- |
   | `PLAYBOOK.md` | The phases, items and criteria, merge-hold list, environment needs, the pinned version and the current room |
   | `DESIGN.md` | The design, and every decision (`D-1`, `D-2`…) with its reasons |
   | `HANDOFF.md` | The last architect session's note |
   | `MISSIONS.md` | The missions and their status. The block at the top shows the current `mission`, `step`, `pr`, `status` and `waiting_for_owner` |
   | `LEDGER.md` | Review findings put off to a later mission or phase |
   | `QODO-VALUE.md` | One line per pull request measuring Qodo |

3. A mission's review records are on its branch and, once merged, on `main`: `reviews/cold/M<k>/` and `reviews/qodo/PR-<n>/`.
4. Or ask the architect:

   ```text
   Where does the build stand? Read the state branch and tell me in a few lines.
   ```

## What you should see

- The files above. `step` names where the current mission is, such as `build`, `cold round 1`, `Qodo round 2`, `gate` or `waiting for owner: gate`.

## If you don't

- No `agent-room/state` branch: the architect hasn't started the project yet ([Start from scratch](start-from-scratch.md)).
- You may edit any file there, but during a phase make changes through the architect, so the lead hears of them ([Change something mid-build](change-something-mid-build.md)).
