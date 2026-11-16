# Troubleshooting

[All manuals](README.md)

## When to use it

Something looks wrong, and the page you were following doesn't cover it.

## What you need first

- What you saw: a buzz, a room message, or what a session printed.

## Steps

1. Find the symptom and do its fix.

   | Symptom | Fix |
   | --- | --- |
   | A Project chat doesn't start with "Operating as architect…" | The rules didn't load: [Create the project's Claude Project](create-the-claude-project.md), "If you don't" |
   | A lead session doesn't start with "Operating as lead…" | The join line wasn't pasted whole, or agent-room is private |
   | Downloading `room.py` fails with 404 | agent-room is still private: [Make agent-room public](make-agent-room-public.md) |
   | `ROOM_NTFY_TOPIC is not set` | The session isn't in the `agent-room` environment, or the variable is missing |
   | `buzz failed: … 403 …` | `ntfy.sh` isn't in the environment's allowed domains |
   | `buzz failed: … 429 …` | [Handle ntfy limit errors](handle-ntfy-limit-errors.md) |
   | Buzz sent, phone quiet | The topic in the app doesn't match the variable exactly, or Android restricts ntfy's battery use |
   | No ACK when the architect said to expect it, after a `DECISION` or `CHANGE` | [Answer a buzz](answer-a-buzz.md), "If you don't" |
   | No `PAUSED` or `STOPPED` buzz about 30 minutes after asking | Send the architect the check line (below the table) ([STOP or PAUSE](stop-or-pause.md), "If you don't") |
   | No `LEAD ONLINE` 10 minutes after starting a lead | Check the session's repository and environment; send the architect the check line (below the table) |
   | A `LEAD-STARTED` with no `LEAD ONLINE` after it, 30 minutes on, `unconfirmed` or not | That lead didn't join. Send the architect the check line (below the table); it starts another. Not sooner: a lead can be slow to start, and a second one would push it out |
   | `NEXT-LEAD-NEEDED` saying `not configured` or `token rejected` | The lead task's token variable is missing, misspelt or old: [Set up the lead task](set-up-the-lead-task.md), "If you don't". Then answer the buzz |
   | A new lead says another lead holds the lease, and ends | If the architect found the old lead gone, use the takeover line it gives you; otherwise a lead is already running ([Start the next lead by hand](start-the-next-lead-by-hand.md)) |
   | A lead started with **Run now** ends at once, saying nothing | The line wasn't pasted whole: the lead task accepts only an exact join line. Copy it again from the architect |
   | `LEAD-SILENT` after your Claude usage ran out | The lead simply stopped. When usage is back, answer the buzz ([Answer a buzz](answer-a-buzz.md)): the architect starts a takeover lead or gives you the takeover line. Or [Move a project to the other account](move-a-project-to-the-other-account.md) |
   | `LEAD-SILENT: no lead joined after DECISION-n` | No lead joined in the three hours after your decision. Answer the buzz ([Answer a buzz](answer-a-buzz.md)): the architect starts one, or finds out with you why its start didn't take (often the lead task's token or Claude usage) |
   | `LEAD-SILENT: still no progress since …` or `still no lead joined after DECISION-n …` | A reminder, every 12 hours while it lasts: nobody has acted on the first alarm, or what was done didn't help. Answer it like the first ([Answer a buzz](answer-a-buzz.md)) |
   | `LEAD-SILENT: state unreadable (…)` | The `agent-room/state` branch or its records are broken, not the lead. [Answer a buzz](answer-a-buzz.md), `LEAD-SILENT`, step 1 |
   | Leads keep ending right after a merge, or at a mission boundary without a `HANDOFF` | A failure drill's `drill:` line is still in `PLAYBOOK.md`. Send the architect the drill line (below the table) |
   | You deleted the lead task | That deleted every lead session it started, the running one too. Send the architect the new-task line (below the table). It sets the task up again with you ([Set up the lead task](set-up-the-lead-task.md)) and records its new ID. If a lead still holds the lease, its session went with the task, so the architect then starts a takeover lead by hand |
   | `NEXT-LEAD-NEEDED` saying `lead task … not found` | The task was deleted, or the playbook names an old one. Send the architect the new-task line (below the table), then answer the buzz |
   | `GitHub access to this repository is not enabled for this session` | Architect chat: approve the repo. Lead: start the session on that repo ([Connect GitHub](connect-github.md)) |
   | `[ignored N message(s) from untrusted authors: X]` | Someone other than you commented; that's ignored by design. If X is another login of yours, add `ROOM_TRUST=X` to the `agent-room` environment |
   | Old `mission/…` branches pile up | Tick **Automatically delete head branches** ([Create the repo](create-the-repo.md), step 3), then delete merged ones on the repo's branches page with the bin icon. Never delete `main` or `agent-room/state` |
   | `MERGE-HOLD` reason 3 though the checks pass, saying the pull request isn't mergeable | Check **Allow merge commits** is ticked in the repo's settings, then answer the buzz |
   | Comments end with "Generated by Claude Code" | Claude's GitHub connection adds it. Harmless |

   The lines the table names:

   - **The check line,** to the architect:

     ```text
     check the room
     ```

   - **The new-task line,** to the architect, with the room number:

     ```text
     The lead task is gone. Set it up again with me (ARCHITECT.md 8.6), record its new ID, then check room N and start a lead if one is needed (9.5).
     ```

   - **The drill line,** to the architect:

     ```text
     The drill is over: remove the drill line.
     ```

2. Nothing matches: send the architect the line below, then describe what you saw.

   ```text
   check the room
   ```

## What you should see

- What the page you were following says you should see.

## If you don't

- [Report a pipeline problem](report-a-pipeline-problem.md), saying which symptom and fix you tried.
