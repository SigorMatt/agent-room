# Glossary

[All manuals](README.md)

## When to use it

To look up a word used in the manuals, the room or a session.

## What you need first

- Nothing.

## Steps

1. Find the word:

   - **Architect:** a chat in the project's Claude Project. It designs with you, owns the design files, kicks off phases and posts your decisions. It never writes code or merges.
   - **Lead:** a Claude Code cloud session that builds one mission, then hands over to the next lead. It runs helpers (builders and reviewers) and merges.
   - **Builder:** a helper of the lead that writes code in its own private copy. It never posts or pushes.
   - **Cold reviewer, Qodo reader, Auditor, Planner:** fresh helpers of the lead that review the code, read Qodo's review, check the review tables, and plan the missions.
   - **Watchdog:** a scheduled task, every three hours per active phase. It buzzes `LEAD-SILENT` when no lead has made progress for three hours, or no lead has joined three hours after your decision, with a reminder every 12 hours while that lasts, and while a request waits on your decision. Before the phase's first lead joins, it only alarms. After that, following a stall's alarm, it starts one lead itself, at most one per stall, but only for a lead that never came: no lead has shown a sign of life since the stall began (posted anything without having handed over, or taken the lease). Never for a lead that joined while waiting for your decision, or while the build is paused or stopped; the architect starts the rest.
   - **Lead task:** one scheduled task per project, with an API trigger, that starts each lead. You create it once ([Set up the lead task](set-up-the-lead-task.md)). The lead and the architect start it with a join line.
   - **Room:** a GitHub issue labelled `agent-room` in the project repo, one per phase, where the architect and the lead talk.
   - **Buzz:** an ntfy push to your phone. It carries the message kind, the project and the room number, never the content.
   - **ntfy topic:** the private name your phone subscribes to. Keep it secret.
   - **Playbook:** `PLAYBOOK.md`, the project's living plan: phases, items with criteria, merge-hold list, environment needs, the pinned version and the current room.
   - **Phase:** a group of playbook items planned and built together, with its own room.
   - **Mission:** one pull-request-sized slice of a phase, on a branch `mission/M<k>-<slug>`. Missions run one at a time.
   - **Task:** one builder's piece of a mission.
   - **State branch:** `agent-room/state`, the branch holding the playbook and all pipeline state. No code; never merged into `main`.
   - **Ledger:** `LEDGER.md`, review findings put off to a named later mission or the next phase.
   - **Escalation:** a lead's question that only you can decide (`ESCALATION-n`).
   - **Merge hold:** a pull request the lead won't merge without you (`MERGE-HOLD-n`).
   - **Decision, change:** the architect's answer to an escalation or hold (`DECISION-n`), and a design change mid-phase (`CHANGE-n`).
   - **ACK:** the lead's receipt for a decision or change.
   - **Starter task:** a one-time scheduled task the architect creates to start one lead through the lead task, named `agent-room start lead SigorMatt/<repo> room N`. Approve it when it appears; a late approval may need a second one. It's given the room's newest comment ID when the architect decided (`0` in a new room), and starts nothing if a lead started or spoke after it (`refused: the room moved on …`). It switches itself off after running; never delete it.
   - **Join line:** the line that starts a lead: the text the lead task is started with, or what you paste into a new Code session.
   - **Takeover line:** a join line that may replace a lead that stopped without handing over. The architect uses it after a `LEAD-SILENT` when the lead is gone; you, only when the architect gives you one.
   - **Sign of life:** any post from a lead that hasn't handed over, or a lead taking the lease. Once a stalled build shows one, the watchdog starts no lead for that stall: the lead may still be working.
   - **Lease:** the record of which session is the lead, so only one lead acts at a time.
   - **Park:** what a lead does when it waits only for your decision: it records that, frees the lease and ends. The lead started after your decision carries on.
   - **Step boundary:** the end of one step of a mission, where a lead reads the room. Why an ACK, a `PAUSE` or a `STOP` can take a while.
   - **Preflight:** the checklist the architect and each lead run on the repo, the state branch and the environment.
   - **Gate:** the checks before every merge: reviews done, every finding decided, checks green, no merge-hold area touched.
   - **Pin, version:** the agent-room release a project uses, on the `pipeline:` line of `PLAYBOOK.md`. `STABLE` names the one new projects get.
   - **Cloud environment:** the `agent-room` settings at claude.ai/code: allowed websites, variables and secrets for leads and the watchdog.
   - **Network secret:** a secret the environment adds to requests for one website, so sessions never see it.
   - **Qodo:** a GitHub app that reviews pull requests; switched by `QODO_REVIEW`.

## What you should see

- The word, with a plain meaning.

## If you don't

- Ask the architect what it means, then [Report a pipeline problem](report-a-pipeline-problem.md) so the word gets added.
