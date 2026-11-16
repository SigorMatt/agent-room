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

A new item in section 3 (Waiting): **"After a container restart."** When a notice says the container restarted:

1. **Nothing else moved.** The lease, the state and the room are as they were, so don't take the lease again or re-post anything. Read the room (`python3 room.py read N lead`) and handle it as at any wake (section 9).
2. **For each stopped builder or reviewer:**
   - Look at its worktree with `git -C <worktree> status --short` and `git -C <worktree> log --oneline -3`. Its commits are kept; its uncommitted edits may be partial.
   - Resume it by sending it a message, using the ID the notice gives. Say that the container restarted, that its uncommitted edits are still in its worktree, and that it should review them, finish its task and report as briefed.
   - If resuming fails (no transcript), start a fresh one with the full brief. Add that the worktree holds a stopped predecessor's uncommitted edits, which it may keep or discard.
   - None of this counts as a failed attempt (5.2, step 4).
3. **A stopped wait or check** (a suite run, a Qodo wait) is run again.
4. **Then post a `STATUS`:** `STATUS: container restarted; resumed <what>`. It is also a sign of life (section 11).
5. **Redo nothing already done.** Whatever was posted, pushed or merged before the restart stands. Check the room and the branch before acting, as after a compaction.

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
