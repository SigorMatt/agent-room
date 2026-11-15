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
| R2-1 | medium | room.py | A stale `waiting_for_owner: yes` mutes the watchdog for good | fixed in 28f33f6 | Reset by `lease take` and by any write that moves the step; regression test |
| R2-2 | medium | room.py | The watchdog takes the room from the block before PLAYBOOK.md | fixed in f473194 | One helper, PLAYBOOK.md first, shared with the gate; regression test |
| R2-3 | medium | room.py | Lease takes, handoffs and intents count as progress, so a looping lead never alarms | fixed in 2f0617c | Progress is a step or pr change, a mission push or a mission PR merge; the loop drill alarms; regression test |
| R2-4 | low | room.py | A status written before a lead died silences the watchdog | fixed in 14b62d3 | Quiet only once the lease is released; regression test |
| R2-5 | low | room.py | An unreadable block makes the watchdog exit without alarming | fixed in 198663a | Reads the last valid block; no state at all alarms "state unreadable"; regression test |
| R2-6 | low | room.py | Any later lead message counts as the closing note | fixed in 74c9545 | Only a trusted lead DONE or STOPPED after `closed_at`; regression test |
| R2-7 | low | room.py | `intent N` accepts another room | fixed in dd9525a | Refuses a room that isn't current; records the room; regression test |
| R2-8 | low | room.py | A moved-aside worktree's `.git` points at the rebuilt one | fixed in 47668cb | The moved copy loses its `.git` link; regression test |
| S1-1 | medium | room.py | A stale `waiting_for_owner` flag mutes the watchdog after later progress | fixed in 7f20d6d | Quiet only while nothing progressed since the flag was set; a pr change resets it; regression test |
| S1-2 | medium | room.py | A transient fetch failure raises a false "state unreadable" alarm | fixed in 5c810b6 | Exits 1 without posting; the alarm needs no state branch or no valid block; regression test |
| S1-3 | medium | room.py | A leftover `close room` intent tells the next phase to close its new room | fixed in 5189b34 | The intent records its room; regression test |
| S1-4 | low | room.py | A new phase's watchdog is muted by the previous phase's status | fixed in aca6ce2 | Pre-start rule: quiet until a lead joins, one alarm after 12h; another room's status never silences; regression test |
| S1-5 | low | room.py | Missing state before the first lead joins alarms overnight | fixed in aca6ce2 | Same pre-start rule; regression test |
