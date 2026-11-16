# M6e spec: a lead survives its container restarting (B-7)

Builds backlog item B-7, from finding W, before M7. It is docs only: `LEAD.md`, one troubleshooting row, `CHANGELOG.md` and `BUILD-STATE.md`. `room.py` doesn't change.

## What happens (finding W)

A cloud session's container can restart in the middle of a session.
- **What survives:** the conversation and the files on disk, uncommitted worktree edits included.
- **What stops:** background subagents and background shell commands.
- **The notice:** the session is woken with a notice that the container was restarted, naming what stopped. A stopped subagent can usually be resumed from its saved transcript by sending it a message, using the agent ID the notice gives. A stopped shell command is lost.
- **What isn't touched:** git, the state branch, the lease and the room.

A lead that doesn't recognise the notice may treat a stopped builder as a failed attempt, start a second builder over the first one's partial edits, or wait forever for a result that won't come.

## `LEAD.md`

A new item in section 3 (Waiting): **"After a container restart."** When a notice says the container restarted (the stopped subagents' work matters: builders never push, so their commits are only on local branches in this container):

1. **Already ended?** If the session already made its last post (`HANDOFF`, `PAUSED`, `STOPPED`, a park, or a drill's end), or stood down (3.4, section 11; cold M6e R2-4), the notice changes nothing: resume nothing, post nothing, end again (section 6, step 4; section 11; cold M6e R1-4).
2. **Check the lease, then read the room** (`python3 room.py lease check`, then `python3 room.py read N lead`); don't take the lease again or re-post anything. Exit 5 from `lease check`: the lead was replaced, so it stands down as section 9 says and resumes nothing (cold M6e R2-4). Otherwise, until resumed, the stopped subagents count as running (cold M6e R1-1).
   - **A `STOP`:** handle it as section 9 says; the stopped subagents stay stopped.
   - **A `PAUSE`:** resume only the stopped builders, which finish, merge and push like running builders before `PAUSED` (section 9).
     - If resuming a builder fails, no fresh one starts: section 9's "start no builders" wins. The `PAUSED` post names it, with its branch and its commits there in this session, such as `builder for T3 stopped by a restart: 2 commits on worktree-agent-B1 in this session, lost`, so Matthew and the next lead know the task must be redone (cold M6e S1-3).
     - A stopped cold reviewer, Qodo reader, planner or auditor isn't resumed (cold M6e R2-1). Before `PAUSED`, the lead commits its own uncommitted records, as section 9 asks for state edits: a dispositions table or a Qodo fetch archive on the mission branch (committed and pushed), and its records in `MISSIONS.md`. The lead that resumes after the `PAUSE` continues the step from what the committed records show, with a fresh subagent only for the part not yet done, such as the audit alone; the partial output is left behind (cold M6e S1-1). A general rule for a resumed review step that finds its round already reported is deferred (B-8).
     - Then points 4 and 5, and the `PAUSE`.
   - **Anything else:** points 3 to 5 first, then handle the room as at any wake (section 9).
3. **Resume each stopped subagent,** of any kind (builder, cold reviewer, Qodo reader, planner, auditor), by message with the ID the notice gives (cold M6e R1-3):
   - **A builder:** first look at its worktree, the newest one recorded under "Tasks in flight" (5.2 step 1 records each builder's worktree path, from the Agent tool's result or `git worktree list`; cold M6e R1-5), with `git -C <worktree> status --short` and `git -C <worktree> log --oneline -3`. Its commits are kept; its uncommitted edits may be partial. The message says that the container restarted, that its uncommitted edits are still in its worktree, and that it should review them, finish its task and report as briefed.
   - **Any other subagent:** "the container restarted; continue and report as briefed" (cold M6e R1-2).
   - **If resuming fails** (no transcript), a fresh one follows its own step's rules (cold M6e R1-2):
     - **A builder:** the full brief. It gets its own new worktree, so the brief adds every earlier worktree path the task's row lists, newest first, and what is in each (commits on its branch, and any uncommitted edits), which it may look at and take over where sound, or ignore (cold M6e S1-4). It adds the stopped builder's last follow-up, if any: a `QUESTION`'s answer, or the failed check's last 10 lines, as in section 9 step 5 (cold M6e R1-7). The task's whole row under "Tasks in flight" is updated: the fresh builder's ID and branch in place of the stopped one's, and its worktree added first in the Worktree column, which keeps every earlier path for the task, newest first. It is committed with `state commit` (cold M6e R1-6, R2-3, S1-4).
     - **A cold reviewer:** first the stopped reviewer's directory is moved aside, `mv /tmp/cold-M<k>-<name> /tmp/cold-M<k>-<name>.stopped`, so the fresh one starts empty and nothing partial is committed (cold M6e R2-2). Then the cold brief and nothing else (5.3 step 2).
     - **A Qodo reader:** its brief. When it reports, every fetch either reader archived is committed (5.5 step 3), so the fetches stay numbered 1 to k.
     - **An auditor:** first the stopped auditor's report is moved aside, `mv /tmp/audit-<kind>-M<k>.md /tmp/audit-<kind>-M<k>.md.stopped` (cold M6e R2-2). Then its brief.
     - **A planner:** its brief.
   - None of this counts as a failed attempt (5.2, step 4).
4. **The lead's own stopped commands are run again:** a suite run, `room.py wait`, a check. A Qodo reader is a subagent: it is resumed (point 3), except under a `PAUSE` (point 2), and not run again (cold M6e R1-3, S1-2).
5. **Then post a `STATUS`:** `STATUS: container restarted; resumed <what>`. It is also a sign of life (section 11).
6. **Redo nothing already done.** Whatever was posted, pushed or merged before the restart stands. Before acting, check the room, `state get step`, the mission branch and any recorded intent, with `reconcile` and its hint as in section 2 step 8 (cold M6e R1-8).

In section 11, the "Delegate" rule ("Resume a builder for follow-ups; if resuming fails, start a fresh one with the full brief") gets a pointer to the new item.

## Manuals

`docs/manual/troubleshooting.md` gets one row:
- **Symptom:** the lead posted `STATUS: container restarted; …`, or a run's log shows a restart.
- **Meaning:** the lead's container restarted, and the lead resumed its builders.
- **What to do:** nothing; the room, lease and state are unchanged.

## Also

- **`CHANGELOG.md`:** an M6e entry.
- **`BUILD-STATE.md`:**
  - B-7 is done in M6e;
  - an M6e milestone row;
  - finding W points to M6e.

## Not in scope

- A restart during a turn that is running (not yet observed).
- The architect's own session: it is Matthew's chat, and he sees what happened.
- Changing how builders are started.

## Tests

`tests/test_docs.py` must keep passing. It checks that every `room.py` command line the docs quote exists. The new item quotes only `room.py read` and `say`, plus git commands.
