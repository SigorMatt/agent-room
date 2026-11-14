# Cold review M2 round 2
covers: 84819f6522aa838a9474a61923b8b5ae0683fe37
base: 895020df2a10f5a84d66519f155e26ac7b9daf43
spec: docs/design/m2-room-cli.md at 84819f6522aa838a9474a61923b8b5ae0683fe37

## Findings

| ID | severity | file:line | finding | failure scenario |
| --- | --- | --- | --- | --- |
| R2-1 | low | room.py:935 | `changed_paths` lists staged paths with `git diff --cached --name-only`, which detects renames, so a renamed or moved lead-owned file shows only its new name and `state commit` skips the lease check (R1-1's guarantee for lead-owned files). | /tmp/cold-m2-r2/e1_rename.py: A holds the lease (gen 1, `step: build`, `pr: 12`). The architect, with no lease, runs `git mv docs/playbook/MISSIONS.md docs/playbook/archive-missions.md` and then `state commit -m tidy`. It exits 0 and MISSIONS.md is gone from the branch. A plain delete of LEDGER.md is refused with exit 5, as it should be. Afterwards A's `lease check`, `say … STATUS` and `state set` all exit 1. The fix every error suggests, `state init-lead`, recreates MISSIONS.md with `lease_generation: 0` and `counter: 0`, so the next `lease take` hands out generation 1 a second time and the next escalation reuses number 1. |
| R2-2 | low | room.py:620 | `check_state_dir`, added for R1-13, refuses any worktree whose HEAD shares no history with the freshly fetched state branch. A state worktree that predates a deleted and recreated `agent-room/state` is therefore refused for good, with the misleading diagnosis "the project checkout?". | /tmp/cold-m2-r2/e2_recreated.py: A has a state worktree and holds the lease. Matthew deletes `agent-room/state` (agents can't delete branches, per Finding A), for example to re-run a rehearsal, and `state init` recreates it as an orphan. In A's worktree, `state sync`, `state path` and `lease check` exit 1 with "holds no agent-room/state history (the project checkout?) … set ROOM_STATE_DIR", `say 1 lead "STATUS: hello"` refuses with "lease check failed", and `preflight --role lead` reports the state branch ✗. Before the fix, `state sync` reset onto the new branch. Now the only remedy, deleting the directory by hand, is never mentioned. |
| R2-3 | low | room.py:885 | `lease_guard` turns any error reading the lease into a refusal. When MISSIONS.md is missing or its block can't be parsed, no session holds a lease, yet every lead `say` and `close` is refused, including the message that would report the problem. | e2_recreated.py, part E3: on a fresh project the first lead runs `preflight --role lead` without `--fix`, which creates its state worktree, and then `say 1 lead "ESCALATION-1: preflight fails, need X"`: exit 1, "not sent: lease check failed: MISSIONS.md is missing". /tmp/cold-m2-r2/e6_broken_block.py: a hand edit on GitHub puts a space between the opening fence's backticks and `agent-room-state`. The holder's `say 1 lead "ESCALATION-1: MISSIONS.md block broken, please fix"` exits 1, and the lead has no channel left to tell Matthew. The spec says a lease that no one holds doesn't block posting. |
| R2-4 | low | room.py:948 | `state commit` parses the pushed MISSIONS.md for its lead-file lease check, and that parse raises when the block is broken. So even the lease holder can't commit the repair, and the lead is wedged until someone edits the branch outside room.py. | e6_broken_block.py: after the fence is broken as in R2-3, holder A runs `state sync`, removes that space from MISSIONS.md and runs `state commit -m "repair block"`. It exits 1 with "MISSIONS.md has no agent-room-state block". `state set`, `lease take` and `lease check` fail the same way, so no room.py command can recover. |
| R2-5 | low | room.py:1002 | `lease take` reports every rejected push as a lost lease race ("another session pushed first; stand down"), even when the push lost to an unrelated state write and the lease is still free. v1 has a lead stand down only when it loses the lease race. | /tmp/cold-m2-r2/e5_take_vs_arch.py: A releases at HANDOFF (`lease_session: none`, gen 1). Successor B's `lease take` overlaps the architect's `state commit` of HANDOFF.md: exit 3, "lease not taken: another session pushed first; stand down". The branch still reads `lease_session: none`, and B's `lease check` prints "held by none". If B follows the message and stands down, there is no lead until LEAD-SILENT (3 h). A `--takeover` after LEAD-SILENT that overlaps the stale lead's `lease release` stands down the same way. |

## Criteria

| criterion | met | evidence |
| --- | --- | --- |
| Tests: fake gh and curl, plus a local bare git remote for state commands | yes | tests/fake_gh_state.py, with bare repos and a second machine cloned from `ROOM_STATE_REMOTE`. The state tests are in the new tests/test_state.py, not added to tests/test_room.py. Both suites pass at this head: 52 ok, "all passed" |
| Tests: session-aware hiding | yes | `t_session_hiding`, including a wiped machine and a legacy message without a session; `t_forged_tag_is_not_own` |
| Tests: `--from` | yes | `t_read_from_and_cursor`: gap messages, `none`, a comment from another room, a missing ID, a bad value |
| Tests: kinds, including hyphenated and multi-word | yes | `t_kinds`, with markdown-wrapped cases |
| Tests: every role-guard rule | yes | `t_role_guard`: each lead and architect deny-list kind, watchdog allow-list, `human`, unknown roles, stdin, wrapped kinds, `close` |
| Tests: auto-buzz kinds | yes | `t_auto_buzz` covers all seven kinds, the title, body and click, never the text, and `--buzz`/`--no-buzz`; `t_close_buzzes_like_say` |
| Tests: lease take/check, including a lost race between two sessions | yes | `t_lease_take_race` (B held at pre-push while A takes the lease), `t_lease_take_stands_down_and_release`, `t_stale_lead_cannot_write` |
| Tests: `state commit` rejection | yes | `t_state_commit_rejected_after_another_push`, `t_state_commit_moved_after_a_fetch`, the single-branch case in `t_single_branch_checkout` |
| Tests: `state next counter` | yes | `t_state_next_counter`, across both machines, plus a non-number |
| Tests: `state init` on an empty repo | yes | `t_state_init_on_empty_repo` |
| Tests: each preflight check's pass and fail | yes | `t_preflight_on_empty_repo`, `_architect_passes`, `_state_branch_fails`, `_push_access`, `_delete_branch_on_merge`, `_approving_reviews`, `_lead` |
| `VERSION = "main"`; links at VERSION | yes | room.py:62 and 150; `t_links_use_version`, including a pinned copy |
| Session ID precedence | yes | room.py:155; `t_session_id`, plus the flag, env and fallback cases in `t_lease_take_race` |
| Repo precedence | yes | room.py:1324; `t_repo_from_checkout` |
| Message format; old format still parsed | yes | room.py:255 and MARK at room.py:68; `t_session_id`, `t_session_hiding` |
| Own messages: same role and session | yes | `is_own` at room.py:170 also requires a trusted author (R1-4) |
| Kinds: multi-word list, then the hyphenated run, after decoration | yes | room.py:77–79 and 207; e.g. `**ESCALATION-3**`, `> PAUSE`, `` `STOP` `` |
| Role guard: exit 2, nothing posted | yes | room.py:220–238; unknown roles are refused |
| Automatic buzz: title, body, click, never the text | yes | room.py:397; e4_buzz.py shows no topic or token in `[buzz failed: …]` for a curl that echoes its argv or hangs |
| Lease check on send: exit 5, a released lease doesn't block, no kind exempt | partly | Correct when MISSIONS.md parses (`t_say_refused_without_lease`). It refuses everything when MISSIONS.md is missing or unparsable (R2-3) |
| `new` | yes | `t_new`, `t_links_use_version` |
| `rooms` | yes | `t_new`, `t_role_guard` |
| `say`: `sent #`, plus a `[buzz …]` line | yes | `t_auto_buzz` |
| `read N ROLE` hides own messages | yes | `t_reply_and_cursor`, `t_session_hiding` |
| `read N ROLE --from ID` | yes | `t_read_from_and_cursor` |
| `read N --all` | yes | `t_untrusted_ignored`, `t_session_id` |
| `wait`: exit codes, `[cursor: ID]` as the last line on exit 0 | yes | `t_wait_cursor_line`, `t_timeout`, `t_close` |
| `close`: closes first, then posts; buzzes like `say` | yes | room.py:500–509; `t_close_buzzes_like_say` |
| `cursor N ROLE` | yes | `t_read_from_and_cursor`; `--from none` prints `none` |
| `ping` | yes | `t_ping`; e4_buzz.py |
| State worktree location; `worktree add` or a shallow clone | partly | `t_state_path_default_location`, `t_single_branch_checkout`, `t_broken_state_worktree_is_rebuilt`. A worktree that predates a recreated branch is stuck (R2-2) |
| `state init` | yes | `t_state_init_on_empty_repo`, `_is_idempotent`, `_on_existing_repo` |
| `state init-lead` | yes | `t_state_init_lead`. Recreating a lost MISSIONS.md resets the generation and the counter (R2-1 scenario) |
| `state path` | yes | `t_local_work_is_not_discarded_silently`, `t_state_path_default_location` |
| `state sync` | yes | `t_local_work_is_not_discarded_silently` |
| `state commit`: exit 3, message, reset; a landed push is a success; lead-owned files need the lease | partly | `t_state_commit_moved_after_a_fetch`, `t_lost_ack_is_a_success`, `t_stale_lead_cannot_write`. A rename skips the lease check (R2-1), and a broken block blocks the holder (R2-4) |
| `state get` | yes | `t_state_set_and_get` |
| `state set`: needs the lease; exit 3 on a lost race | yes | `t_stale_lead_cannot_write` covers exit 5. The lost race uses the same `change_state`/`commit_and_push` path as `lease take`'s tested race, but has no test of its own |
| `state next counter`: needs the lease | yes | `t_state_next_counter`, `t_stale_lead_cannot_write` |
| `lease take [--takeover]` | partly | Stands down while another session holds the lease (`t_lease_take_stands_down_and_release`). It also stands down after losing to an unrelated push (R2-5) |
| `lease release` | yes | `t_lease_take_stands_down_and_release`: the holder only; the generation is kept |
| `lease check` | yes | `t_lease_take_race` |
| Machine block: one block, single-line values, unknown keys kept | yes | `t_state_set_and_get`, `t_state_set_rejects_any_line_break` |
| Preflight: push access | yes | `t_preflight_push_access` |
| Preflight: `main` has commits | yes | `t_preflight_on_empty_repo` |
| Preflight: approving reviews; 404 and 403-upgrade mean none | yes | `t_preflight_approving_reviews` |
| Preflight: admin bypass, report only | yes | `t_preflight_approving_reviews` |
| Preflight: `delete_branch_on_merge` | yes | `t_preflight_delete_branch_on_merge` |
| Preflight: state branch, PLAYBOOK.md, DESIGN.md and a `pipeline: v…` pin, from the pushed branch; `main` warns | yes | `t_preflight_architect_passes`, `t_preflight_state_branch_fails` |
| Preflight: lead-owned files, `--fix` | yes | `t_preflight_lead`; uncommitted copies don't count |
| Preflight: ROOM_NTFY_TOPIC set; QODO_REVIEW on or off | yes | `t_preflight_lead`; the topic is never printed |
| Preflight exits 0 only with no ✗ | yes | room.py:1212–1214 |

## Round 1 fixes

| ID | holds | evidence |
| --- | --- | --- |
| R1-1 | partly | `state set`, `state next` and `lease release` check the lease after the sync (room.py:850). `t_stale_lead_cannot_write` passes, and the e1 sequence from round 1 now exits 5. The lead-file check in `state commit` is bypassed by a rename (R2-1) |
| R1-2 | yes | The base is the merge-base of HEAD and the tracking ref (room.py:713), so a fetch from `lease check` or from `git fetch` in the checkout still gives exit 3 and a reset worktree (`t_state_commit_moved_after_a_fetch`). I traced several cases by hand: several unpushed commits, an earlier lost ack, a push failure with no move. Each ends in the right outcome |
| R1-3 | yes | `lease take` exits 3 while another session holds the lease, `--takeover` overrides, and `lease release` frees it (`t_lease_take_stands_down_and_release`). The spec and BUILD-STATE were updated to match. See R2-5 for the stand-down after an unrelated push |
| R1-4 | yes | `is_own` requires a trusted author (room.py:174). `t_forged_tag_is_not_own` passes, both without a cursor and with one, and warns about the ignored message |
| R1-5 | yes | `close` buzzes and takes `--buzz`/`--no-buzz` (room.py:509); `t_close_buzzes_like_say` |
| R1-6 | yes | DECORATION strips leading whitespace, `*`, `_`, backticks, `>` and `#` (room.py:77). The guard and the buzz see wrapped kinds (`t_kinds`, `t_role_guard`, `t_auto_buzz`). Text like "> **Note**" or "Re: DECISION-3" still parses as no kind |
| R1-7 | yes | No exemption remains; `LEAD ONLINE`, and `LEAD ONLINE` followed by MERGE-HOLD text, are refused without the lease (`t_say_refused_without_lease`) |
| R1-8 | yes | Only `POSTING_ROLES` may post (room.py:223); `leader`, `builder` and `planner` exit 2, for `say` and for `close` (`t_role_guard`) |
| R1-9 | yes | The check uses `splitlines()` itself (room.py:971), so it covers every separator by construction. The test uses literal U+2028 and U+2029, among others |
| R1-10 | yes | Timeout and OSError messages carry no argv, and stderr is scrubbed (room.py:376–389). `t_buzz_errors_hide_secrets` passes. In e4_buzz.py, real `say` and `ping` runs with a curl that echoes its argv, or hangs for 40 s, print `***` for the topic and the token |
| R1-11 | yes | A remote that already holds HEAD counts as a success (room.py:720); `t_lost_ack_is_a_success`, and the lost-ack part of `t_lease_take_stands_down_and_release` |
| R1-12 | yes | A dangling worktree is moved aside and rebuilt (room.py:633–640); `t_broken_state_worktree_is_rebuilt` |
| R1-13 | yes | A directory with another branch checked out, or with no state-branch history, is refused before any reset (`t_refuses_a_dir_that_is_not_the_state_worktree`). The same check introduced R2-2 |
| R1-14 | yes | Preflight reads `origin/agent-room/state` after a fetch (room.py:1153–1166, 1185); uncommitted pins, deletions and lead files don't count (`t_preflight_architect_passes`, `t_preflight_lead`) |
| R1-15 | yes | Only `main` warns, other values that aren't tags fail, and a missing line gets its own fix text (`t_preflight_state_branch_fails`). The spec row was updated to allow `main` |

## Scope

Beyond the spec, the diff includes:

- docs: BUILD-STATE.md (M0 done, milestones renamed, Finding F, decisions including the lease release of 2026-11-15), the round-1 report and its dispositions under `reviews/cold/M2/`, and the M2 spec itself;
- the playbook templates under `templates/playbook/`, which room.py downloads at VERSION when it runs alone;
- the `ROOM_STATE_REMOTE` variable;
- `read --from none`;
- `state init` also restores missing architect files and refuses a repo that has branches but no `main`;
- `state next` accepts any key;
- `lease release` refuses a session that doesn't hold the lease (exit 5);
- broken state worktrees are moved aside and rebuilt, and directories that aren't the state worktree are refused;
- preflight adds a summary line and checks that MISSIONS.md parses;
- tests/fake_gh.py writes atomically and answers a single-comment GET;
- the state tests live in a new tests/test_state.py with tests/fake_gh_state.py, instead of extending tests/test_room.py as the spec says.

Every row of the spec's tables has an implementation, and every bullet of its Tests paragraph has a test. The only spec behaviour without a direct test is `state set`'s exit 3 on a lost race, which runs through the same tested code as `lease take`'s lost race. I reviewed head 84819f6 with a clean working tree. The two excluded draft specs were not read.
