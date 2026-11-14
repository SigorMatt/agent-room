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
