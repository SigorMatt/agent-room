# Cold dispositions, M4

| ID | severity | file | finding | disposition | evidence |
| --- | --- | --- | --- | --- | --- |
| R1-1 | medium | room.py | Auto-deleted branches and step-less merges look like no progress | fixed in 93fb58e | Progress is any state write other than the cursor, a mission push, or a merged mission PR from this repo; regression test |
| R1-2 | medium | room.py | A stale `status` silences the watchdog for good | fixed in 5e20122 | `lease take` sets `status: running`; regression test |
| R1-3 | medium | room.py | An alarm whose buzz failed is never retried | fixed in 6ab17c9 | Buzz first, then post with `(buzz sent)` or `(buzz failed: …)`; failed alarms don't dedupe; regression test |
| R1-4 | medium | room.py | A fork PR with the mission branch name steers reconcile | fixed in cab51db | Only PRs from this repo by a trusted author into main count; regression test |
| R1-5 | medium | room.py | `handoff` records the waiter-moved cursor, skipping unacted messages | fixed in ca1d4f3 | `--cursor ID` is required, checked to be in the room, and recorded; regression test |
| R1-6 | medium | room.py | `ROOM_TRUST` replaces the gh login instead of adding to it | fixed in 0f648ab | Logins are added; README line fixed; regression test |
| R1-7 | medium | room.py | A successor's `lease take` stands down after losing to an unrelated write | fixed in d938e1a | Fixed in M2 (cold M2 R2-5); handoff-specific regression test in dd9df73 |
| R1-8 | low | room.py | Any non-`running` status silences the watchdog | fixed in 2100ad3 | Quiet only for paused, stopped or done, any case; regression test |
| R1-9 | low | room.py | `waiting_for_owner: yes` is ignored | fixed in 2100ad3 | Honoured, as is a step starting with "waiting for owner"; regression test |
| R1-10 | low | room.py | A leftover watchdog of an earlier room alarms | fixed in 2100ad3 | Quiet with a note when the room isn't the current one; regression test |
| R1-11 | low | room.py | Closed, unmerged PRs get wrong hints | fixed in cab51db | Both PR intents handle them; regression test |
| R1-12 | low | room.py | A `close room` intent counts as done without the closing note | fixed in c7ccc0c | Needs a trusted lead message after `closed_at`; regression test |
| R1-13 | low | room.py | Post intents compare clocks | fixed in 696504f | `room.py intent` records `post KIND after #<id>`; reconcile compares comment IDs; regression test |
| R1-14 | low | room.py | A re-recorded post intent is satisfied by an older post | fixed in 696504f | The new intent records a new comment ID; regression test |
| R1-15 | low | room.py | Budget parsing falls back to 8 hours on common variants | fixed in 145bbe3 | Emphasis, h/hr/hrs/hour(s) and decimals accepted; regression test |
| B-2 | low | room.py | Deferred from cold M2 S1-3, S1-4, S1-5: stale state worktrees | fixed in c1027f5 | A marker in the worktree's git dir decides what may be rebuilt, whatever the current directory; HEAD and uncommitted work saved on `refs/agent-room/broken-<stamp>` first; regression tests; the four repros |
