# Cold dispositions, M6e

M6e's records are kept under `reviews/cold/M9/`, because the gate's exempt patterns name missions `M<digits>` (M6b's are under `M6`, M6d's under `M8`).

| ID | severity | file | finding | disposition | evidence |
| --- | --- | --- | --- | --- | --- |
| R1-1 | high | LEAD.md | Step 7 handled the room before resuming stopped builders, so a `PAUSE` ended the session and their unpushed commits were lost | fixed in 65f879f | Step 7 reads the room first; stopped subagents count as running until resumed. A `STOP` leaves them stopped; anything else, a `PAUSE` included, resumes them before the room is handled, so a `PAUSE` lets them finish before `PAUSED`. The intro says builders never push, so their commits are only local |
| R1-2 | medium | LEAD.md | A fresh cold reviewer was handed the stopped one's notes, losing the round's independence, and the resume message spoke of worktree edits to every subagent | fixed in 65f879f | A fresh subagent follows its own step's rules: a cold reviewer gets the cold brief and nothing else (5.3 step 2); only a builder's resume message mentions worktree edits |
| R1-3 | medium | LEAD.md | A stopped Qodo reader was both "resume it" and "run it again", and planners and auditors had no rule | fixed in 65f879f | Step 7 covers every kind of subagent (builder, cold reviewer, Qodo reader, planner, auditor), resumed by message; "run again" is only for the lead's own commands; a fresh reader's report commits every fetch either reader archived (5.5 step 3) |
| R1-4 | medium | LEAD.md | A session that had made its last post (`HANDOFF`, `PAUSED`, `STOPPED`, a park, a drill's end) would resume builders and post a `STATUS` after it | fixed in 65f879f | New point 1: after its last post, a session resumes nothing, posts nothing and ends again (section 6 step 4, section 11) |
| R1-5 | low | LEAD.md | Nothing recorded a builder's worktree, so the lead couldn't find it after a restart | fixed in 65f879f, 668e595 | 5.2 step 1 records each builder's worktree path under "Tasks in flight"; the MISSIONS.md template's table now has Task, Builder, Worktree, Branch, Attempt and Status |
| R1-6 | low | LEAD.md | A fresh builder replacing a stopped one wasn't recorded under "Tasks in flight" | fixed in 65f879f | Its ID replaces the stopped one's, committed with `state commit` |
| R1-7 | low | LEAD.md | The fresh builder didn't get the stopped one's last follow-up | fixed in 65f879f | It also gets the `QUESTION`'s answer or the failed check's last 10 lines, as in section 9 step 5 |
| R1-8 | low | LEAD.md | "As after a compaction" pointed to a rule that doesn't say what to check | fixed in 65f879f | Point 6 names the room, `state get step`, the mission branch and any recorded intent via `reconcile N` (section 2 step 8) |
