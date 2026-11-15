# Cold dispositions, M2

| ID | severity | file | finding | disposition | evidence |
| --- | --- | --- | --- | --- | --- |
| R1-1 | high | room.py | `state set` / `state next` write without checking the lease | fixed in bb27a4e | Writes by a session that doesn't hold the lease exit 5; regression test in tests/test_state.py; repro e1 adapted |
| R1-2 | high | room.py | A failed push is judged against the tracking ref, not the work's base | fixed in 4d43ec1 | Base is the merge-base of HEAD and the remote; a moved branch exits 3 after any fetch; regression test; repro e3 |
| R1-3 | medium | room.py | Two successors launched apart both win the lease | fixed in bb27a4e | `lease take` exits 3 while another session holds the lease unless `--takeover`; `lease release` added; spec and BUILD-STATE decision 2026-11-15 |
| R1-4 | medium | room.py | With no cursor, a forged role and session tag hides trusted messages | fixed in c8e50d3 | Untrusted comments never count as own; regression test; repro e4 |
| R1-5 | medium | room.py | `close` never buzzes, so `DONE` via `close` doesn't reach Matthew | fixed in ffb4ab5 | `close` buzzes like `say`, with `--buzz`/`--no-buzz`; regression test; repro e9 E10 |
| R1-6 | medium | room.py | Kinds wrapped in markdown parse as no kind, skipping buzz and role guard | fixed in e6d2fff | Leading decoration is stripped before kind parsing; regression test; repro e9 E11 |
| R1-7 | low | room.py | The `LEAD ONLINE` exemption lets a lease-less lead post anything | fixed in bb27a4e | Exemption removed; the guard refuses only when another session holds the lease; regression test |
| R1-8 | low | room.py | Unknown roles post any kind without checks | fixed in ca4e268 | Only lead, architect and watchdog may post; regression test |
| R1-9 | low | room.py | Unicode line separators inject keys into the machine block | fixed in b20caaf | Values that `splitlines()` would split are rejected; regression test; repro e5 |
| R1-10 | low | room.py | A curl timeout echoes the ntfy topic and token | fixed in 2ddd571 | Buzz errors never echo argv; topic and token masked; regression test; repro e6 |
| R1-11 | low | room.py | A push that landed but lost its ack is reported as lost | fixed in 4d43ec1 | A remote that already holds the commit counts as success; regression test; repro e12 |
| R1-12 | low | room.py | A stale state worktree breaks every state command | fixed in 4da4815 | A broken worktree is moved aside and rebuilt; regression test; repro e7 |
| R1-13 | low | room.py | `ROOM_STATE_DIR` pointed at the project checkout destroys work | fixed in 4da4815 | A dir with another branch checked out, or sharing no history with the state branch, is refused; regression test; repro e7 E8 |
| R1-14 | low | room.py | Preflight passes on uncommitted local state | fixed in c651f2f | Preflight reads the pushed branch; regression test; repro e9 E9 |
| R1-15 | low | room.py | Non-tag pins only warn; a missing pin suggests `state init` | fixed in c651f2f | Only `pipeline: main` warns (development builds, per the updated spec); others fail; a missing pin says how to add it; repro e9b |
| R2-1 | low | room.py | A renamed or moved lead-owned file skips the lease check in `state commit` | fixed in 146889e | Staged paths are listed with `--no-renames`; regression test; repro e1_rename |
| R2-2 | low | room.py | A state worktree predating a recreated state branch is refused for good | fixed in ea80f57 | A stale state worktree is moved aside and rebuilt; the project checkout is still refused; regression test (dated in 4721541); repro e2 |
| R2-3 | low | room.py | An unreadable lease blocks every lead `say` and `close` | fixed in 2dd7a48 | They post with a warning when MISSIONS.md is missing or its block unparseable; git errors still refuse; regression test (fixed in 354c618); repro e2 E3, e6 |
| R2-4 | low | room.py | `state commit` can't repair a broken block | fixed in 6334a71 | The commit goes ahead with a warning while the pushed lease is unreadable; regression test; repro e6 |
| R2-5 | low | room.py | `lease take` stands down after losing to an unrelated write | fixed in d938e1a | Re-syncs and retries once if the lease is free, ours or unchanged; stands down only if another session took it; regression test; repro e5 |
| S1-1 | medium | room.py | While the block is unreadable, any session can commit lead-owned changes | fixed in 56dcb71 | The last `lease_session:` line still decides; another session is refused (exit 5); regression test `t_broken_fence_still_names_the_holder`; repro e4 |
| S1-2 | low | room.py | While the block is unreadable, a superseded lead can post and close | fixed in 56dcb71 | Same rule for `say` and `close`; regression test; repro e8 |
| S1-3 | low | room.py | A stale worktree with local work is moved aside silently and loses its commits | fixed in 3e1d1ba | Deferred first (B-2), then fixed in M2 after Qodo PR #6 marked it Action required; regression test |
| S1-4 | low | room.py | From outside the checkout, a misconfigured state dir naming the project checkout is moved aside | fixed in 3e1d1ba | Deferred first (B-2), then fixed in M2 after Qodo PR #6 marked it Action required; regression test |
| S1-5 | low | room.py | From inside a stale state worktree, R2-2 is still unfixed | fixed in 3e1d1ba | Deferred first (B-2), then fixed in M2 after Qodo PR #6 marked it Action required; regression test |
| S2-1 | medium | room.py | A quoted `lease_session:` line decides the holder once the fence breaks | fixed in 8cd9599 | Line scanning removed; the lease is the last block that parses in the branch history; regression test |
| S2-2 | medium | room.py | A takeover can't get through a broken block | fixed in 8cd9599 | `lease take --takeover` starts from the last valid block and repairs it; regression test |
| S2-3 | medium | room.py | A holder commit can drop or break the block | fixed in 8cd9599 | Commits changing MISSIONS.md must keep a valid block with the current lease, for everyone; regression test |
| S3-1 | medium | room.py | With the closing fence deleted by hand, the block runs on into a later fenced quote, which then decides the lease | fixed in 10c6583 | Deferred first (B-3), then fixed in M2 after Qodo PR #6 marked it Action required; regression test |
| S3-2 | medium | room.py | With the opening fence damaged by hand, a quoted second `agent-room-state` block becomes the lease | fixed in 10c6583 | Deferred first (B-3), then fixed in M2 after Qodo PR #6 marked it Action required; regression test |
| S3-3 | low | room.py | Repairing a block that also lost its closing fence deletes the records up to the next fence | fixed in 10c6583 | Deferred first (B-3), then fixed in M2 after Qodo PR #6 marked it Action required; regression test |
