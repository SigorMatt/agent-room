# Files and owners

[All manuals](README.md)

## When to use it

To find where something lives, and who changes it.

## What you need first

- Nothing. For the files themselves: [Read the design and state on the state branch](read-the-state-branch.md).

## Steps

1. Where the pieces live:

   | Piece | Where | Changed by |
   | --- | --- | --- |
   | agent-room: `room.py`, protocols, manuals, `CHANGELOG.md`, `STABLE` | `SigorMatt/agent-room`, public | Releases (tags such as `v1.0.0`) |
   | The `agent-room` skill | Each Claude account | You, rarely |
   | A Claude Project per project | Claude app | You |
   | The `agent-room` cloud environment | claude.ai/code | You |
   | The lead task, one per project, and its token | claude.ai/code/routines, and the environment's variables | You, once per project ([Set up the lead task](set-up-the-lead-task.md)) |
   | The watchdog, one per phase | Scheduled tasks | The architect: created at kickoff, deleted at `DONE` |
   | ntfy subscription | Your phone | You |
   | The project's code | Its repo, `main` | Merged mission pull requests only |
   | The design and pipeline state | Its repo, branch `agent-room/state` | The architect and the lead, directly |

2. Files on `agent-room/state`, under `docs/playbook/`. Each agent edits only its own and reads all. You may edit any.

   | File | Owner | Holds |
   | --- | --- | --- |
   | `PLAYBOOK.md` | Architect | Version pin, repo, room, the watchdog's and the lead task's IDs, test command; phases; items and criteria; merge-hold list; environment needs; lead's discretion; Phase 0 known debt |
   | `DESIGN.md` | Architect | Goals, architecture, interfaces, data; the decision log `D-n` |
   | `HANDOFF.md` | Architect | The last architect session's note |
   | `DIGEST.md`, `SURVEY.md` | Architect | From starting with a discussion, or a discussion plus code |
   | `MISSIONS.md` | Lead | Missions and status; the current step; who the lead is |
   | `LEDGER.md` | Lead | Findings put off, each with its target |
   | `QODO-VALUE.md` | Lead | One line per pull request measuring Qodo |

3. Review records travel with the code, on the mission branch and then on `main`: `reviews/cold/M<k>/` and `reviews/qodo/PR-<n>/`.

## What you should see

- These files on GitHub, in those places.

## If you don't

- No `agent-room/state` branch: the project hasn't started ([Start from scratch](start-from-scratch.md)).
- A lead-owned file is missing: the lead creates it when it joins.
