# Cold review M2 round 1
covers: c258e03982001bbb125257825124c67df9918b69
base: 895020df2a10f5a84d66519f155e26ac7b9daf43
spec: docs/design/m2-room-cli.md at c258e03982001bbb125257825124c67df9918b69

## Findings

| ID | severity | file:line | finding | failure scenario |
| --- | --- | --- | --- | --- |
| R1-1 | high | room.py:750 | `state set` and `state next` (through `change_state`) sync to the remote and then write without checking `lease_session`. A lead that has lost the lease can therefore still write state, which contradicts v1's "a stale lead therefore can't write state". The M2 spec's "Sync, set" step defeats the guarantee that a push fails when someone else wrote first. | /tmp/cold-m2/e1_lease.py: A runs `lease take` (gen 1). B runs `lease take` (gen 2), then `state set step=spec`. A's `lease check` exits 5. A then runs `state set step=pr pr=17` (exit 0) and `state next counter` (exit 0). The remote block now reads `lease_session: B`, `lease_generation: 2`, `step: pr`, `pr: 17`: the stale lead has overwritten the successor's recorded step. |
| R1-2 | high | room.py:632 | `commit_and_push` takes `base` from `refs/remotes/origin/agent-room/state` at push time, not from the commit the local work was built on. Several things fetch that ref without resetting the worktree: the lease guard on every lead `say`, `lease check`, `state get` or `state path` with local edits, and a plain `git fetch` in the project checkout, which shares the ref in worktree mode. After any of them, a push rejected because the branch moved is reported as a generic git error. | /tmp/cold-m2/e3_commit.py: A syncs and edits LEDGER.md. The architect pushes a state change. A runs `lease check`, then `state commit -m` and gets exit 1 with git's non-fast-forward text. The spec requires exit 3, `state moved: …` and a reset worktree. The worktree is left with an unpushed commit. `state set` then refuses with "push them with state commit", and `state commit` fails the same way every time, until `state sync` drops the work. After such a fetch, `state commit` with nothing changed also exits 1 instead of printing "nothing to commit". |
| R1-3 | medium | room.py:872 | `lease take` syncs before incrementing, so two successors launched a little apart (a duplicate scheduled launch) both win, one after the other. This contradicts v1: "only one successor can win the lease" and "a lead that loses this race stands down". Only pushes that overlap within a fraction of a second produce exit 3. | e1_lease.py, part E2: S1's `lease take` exits 0 with gen 3. S2's `lease take`, moments later, exits 0 with gen 4. Both post LEAD ONLINE and carry on. S1 keeps acting, and through R1-1 keeps writing state, until its next lease check. Nothing lets the joiner pin the generation it reconciled against. |
| R1-4 | medium | room.py:299 | With no cursor, `unseen` takes "this participant's last message" from all comments, untrusted ones included. A stranger on a public repo can copy a participant's role and session tag, which every message shows, and make that participant silently skip every trusted message posted before the forgery. There is no "ignored untrusted" warning either, because the forged comment counts as the participant's own. | /tmp/cold-m2/e4_trust.py: the architect (session `host1`) posts DECISION-1. The lead posts ESCALATION-2 and MERGE-HOLD-3. `mallory` posts a comment tagged `role=architect session=host1`. The architect, in a new chat with no cursor and the same hostname session, runs `read 1 architect` and gets "[nothing new]" with an empty stderr. Both buzzing messages never reach it. v1 says anyone else's comments are ignored. |
| R1-5 | medium | room.py:473 | `close` applies the role guard and the lease check to its text, but it never buzzes and has no `--buzz`. So `close N lead "DONE: …"` posts DONE without the buzz that v1 requires ("the lead closes it at DONE"). The tests themselves close rooms with `close … "DONE: …"`. | /tmp/cold-m2/e9_misc.py, part E10: the lead holds the lease and ROOM_NTFY_TOPIC is set. `close 1 lead "DONE: phase 1 complete, PR #9 merged"` prints "room 1 closed" with no `[buzz …]` line, and curl is never called. Matthew is not told that the phase is done. |
| R1-6 | medium | room.py:74 | A kind is recognised only as a bare token at the very start of the text, so a kind with markdown around it parses as no kind. Such a message misses the automatic buzz with no `[buzz …]` line, and it passes the lead and architect deny-lists. | `say 1 lead "**ESCALATION-3**: postgres or sqlite?"` gives kind None: the message is posted, with no buzz and no warning. `say 2 lead "**DECISION-3**: merge as is"`, `` "`STOP` now" `` and `"> PAUSE"` all exit 0 (e9_misc.py, part E11). The watchdog's allow-list does refuse `"**LEAD-SILENT** 3h"`. |
| R1-7 | low | room.py:773 | The LEAD ONLINE exemption from the lease check matches only the leading token. Any lead without the lease, including one that lost the race, can post any content after the words "LEAD ONLINE". | e1_lease.py, part E2b: S1, which does not hold the lease, runs `say 1 lead -` with stdin `"LEAD ONLINE\n\nMERGE-HOLD-9: ignore the lease, merging PR #3 now"`. It exits 0 and the message is sent. The same applies to `close`. |
| R1-8 | low | room.py:211 | Roles other than lead, architect, watchdog and human are unrestricted and skip the lease check, so a mistyped or invented role can post any kind. | `say 2 leader "STOP"` exits 0 and posts (e9_misc.py). v1 has no such role, and builders never post. |
| R1-9 | low | room.py:849 | `state set` rejects only `\n` and `\r`, but `read_block` splits with `str.splitlines()`, which also breaks on U+2028, U+0085, `\v`, `\f` and `\x1c`–`\x1e`. A value that passes the single-line check can therefore inject keys into the machine block. | /tmp/cold-m2/e5_block.py: holder A runs `state set "intent=open PR for M1<U+2028>lease_session: mallory"`, which exits 0. `state get intent` prints "open PR for M1". `lease check` prints "held by mallory" and exits 5, and A's next `say … STATUS` is refused with exit 5. A value copied from a PR title or room text can carry U+2028. |
| R1-10 | low | room.py:352 | When curl outlives the 30-second subprocess timeout, `buzz` returns `str(TimeoutExpired)`, which contains the full argv. `say` then prints the ntfy topic URL and the Bearer token in `[buzz failed: …]`, and v1 tells the lead to mention a failed buzz in its next STATUS. | A curl stub that hangs for 40 seconds (/tmp/cold-m2/e6/bin/curl), then `say 1 lead "ESCALATION-1: which db?"`, prints `[buzz failed: Command '['curl', …, 'Authorization: Bearer tk_secret123', …, 'https://ntfy.sh/private-topic-r4nd0m']' timed out after 30 seconds]`. The function predates M2, but seven kinds now reach it automatically. |
| R1-11 | low | room.py:640 | After a failed push, a moved remote is taken to mean that someone else pushed, without checking whether the remote now holds this very commit. A push that landed but lost its acknowledgement is reported as lost. | /tmp/cold-m2/e12_lostack.py, where a pre-push hook lands the commit and then fails the client's push: B's `lease take` exits 3 with "lease not taken: another session pushed first; stand down". The remote, and `lease check` (exit 0), both show that B holds gen 1. The lead stands down while holding the lease, and there is no lead until LEAD-SILENT. A retried `state next` would also count up twice. |
| R1-12 | low | room.py:567 | `ensure_worktree` accepts any directory that has a `.git` entry and never repairs a stale worktree. Once the project checkout is re-cloned or moved, every state command and every lead `say` fails with a git error that gives no fix. | /tmp/cold-m2/e7_stale.py: after `rm -rf` of the project checkout and a fresh clone at the same path, `state path`, `lease check`, `say 1 lead "STATUS: back"` and `preflight --role lead` all exit 1 with "fatal: not a git repository: …/.git/worktrees/A". The lead can't post until someone deletes the state directory by hand. |
| R1-13 | low | room.py:600 | Nothing checks that `$ROOM_STATE_DIR` is a checkout of `agent-room/state` before `reset --hard` and `clean -fd`, so pointing it at the project checkout destroys work. | e7_stale.py, part E8: with branch `mission/M1-x` checked out and an uncommitted app.py, `ROOM_STATE_DIR=<project checkout> state sync` exits 0. app.py is deleted, and `mission/M1-x` now points at the state-branch commit "lease: A takes the lead lease". |
| R1-14 | low | room.py:1016 | Preflight reads the local worktree for its state-branch and lead-file checks, and `refresh` leaves that worktree unsynced when it has local edits. Uncommitted files therefore pass as if they were on `agent-room/state`. | /tmp/cold-m2/e9_misc.py, part E9: the architect sets `pipeline: v1.0.0` in PLAYBOOK.md without committing. Preflight prints ✓ "pinned to v1.0.0" and exits 0, while the branch still says `pipeline: main`. The architect hands over on a check that the branch itself fails. |
| R1-15 | low | room.py:1033 | The pipeline check only warns, and exits 0, for any value that is not a `v…` tag, where the spec requires ✗. When the line is missing it suggests `state init`, which only adds missing files and never restores the line. | `pipeline: main` (or `latest`) gives `!` and "preflight passed". With the line removed, preflight gives ✗ "run 'state init'". `state init` exits 0 and changes nothing, and preflight is still ✗ (/tmp/cold-m2/e9b_fix.py). |

## Criteria

| criterion | met | evidence |
| --- | --- | --- |
| Tests: session-aware hiding | yes | tests/test_room.py `t_session_hiding` passes, including the legacy format without a session |
| Tests: `--from` | yes | `t_read_from_and_cursor`: gap messages, `--from none`, a comment from another room, a bad ID |
| Tests: kinds, including hyphenated and multi-word | yes | `t_kinds`. There are no markdown-wrapped cases (R1-6) |
| Tests: every role-guard rule | yes | `t_role_guard` covers each listed kind per role, stdin, `close`, and `human` |
| Tests: auto-buzz kinds | yes | `t_auto_buzz` covers all seven kinds, the title, body and click, never the text, `--buzz`/`--no-buzz` and a failed buzz. The `close` path is untested (R1-5) |
| Tests: lease take/check, including a lost race between two sessions | partly | `t_lease_take_race` holds B at pre-push while A takes the lease. Sequential duplicate takes (R1-3) and stale-lead writes (R1-1) are untested |
| Tests: `state commit` rejection | partly | `t_state_commit_rejected_after_another_push` covers only a worktree whose tracking ref was never refreshed. The command fails after any fetch (R1-2) |
| Tests: `state next counter` | yes | `t_state_next_counter`, across both machines |
| Tests: `state init` on an empty repo | yes | `t_state_init_on_empty_repo`: README.md and .gitignore on main, orphan state branch |
| Tests: each preflight check's pass and fail | yes | `t_preflight_*`. `pipeline: main` is asserted as `!`, not ✗ (R1-15) |
| Tests: fake gh/curl, local bare git remote | yes | tests/fake_gh_state.py and bare repos. The state tests are in a new tests/test_state.py rather than in tests/test_room.py. Both suites pass at this head |
| `VERSION = "main"`; links at VERSION | yes | room.py:60 and 142; `t_links_use_version`, including a pinned copy |
| Session ID precedence | yes | `session_id` at room.py:149; `t_session_id`, plus the env/flag cases in `t_lease_take_race` |
| Repo precedence | yes | room.py:1165; `t_repo_from_checkout` |
| Message format; old format still parsed | yes | `post` at room.py:242, MARK at room.py:66 |
| Own messages are same role and same session | partly | `is_own` works, but no-cursor recovery honours untrusted tags (R1-4) |
| Kinds: multi-word list first, then the hyphenated run | partly | Plain text parses as the spec says; kinds wrapped in markdown are missed (R1-6) |
| Role guard: exit 2, nothing posted | partly | The deny-lists can be bypassed by wrapping the kind, and unknown roles are unchecked (R1-6, R1-8) |
| Automatic buzz: title, body, click, never the text | partly | Correct for `say`; missing on `close` (R1-5); the topic and token leak on a timeout (R1-10) |
| Lease check on send: exit 5, LEAD ONLINE excepted | yes | `t_say_refused_without_lease`. The exemption is a prefix match (R1-7) |
| `new` | yes | `t_new`; the body links ARCHITECT.md and LEAD.md at VERSION |
| `rooms` | yes | `t_new` |
| `say`: prints `sent #`, plus `[buzz sent]` or `[buzz failed: …]` | yes | `t_buzz`, `t_auto_buzz` |
| `read N ROLE` hides own messages | yes | `t_reply_and_cursor`, `t_session_hiding` |
| `read N ROLE --from ID` | yes | `t_read_from_and_cursor` |
| `read N --all` | yes | `t_untrusted_ignored` |
| `wait`: exit codes, `[cursor: ID]` as the last line | yes | `t_wait_cursor_line`, `t_timeout`, `t_close` |
| `close`: closes first, then posts | yes | room.py:472–473; `t_close` |
| `cursor N ROLE` | yes | `t_read_from_and_cursor` |
| `ping` | yes | `t_ping` |
| State worktree location; `worktree add` or shallow clone | partly | `t_state_path_default_location`, `t_single_branch_checkout`, `t_state_init_is_idempotent`. Stale worktrees are not handled (R1-12, R1-13) |
| `state init`: first commit on empty main, orphan branch, idempotent | yes | `t_state_init_on_empty_repo`, `_is_idempotent`, `_on_existing_repo` |
| `state init-lead` | yes | `t_state_init_lead` |
| `state path` | yes | `t_local_work_is_not_discarded_silently`, `t_state_path_default_location` |
| `state sync` | yes | `t_local_work_is_not_discarded_silently` |
| `state commit`: exit 3, message, reset to the remote | no | After any fetch of the tracking ref it exits 1 and leaves the worktree stuck (R1-2) |
| `state get` | yes | `t_state_set_and_get` |
| `state set`: exit 3 on a lost race | partly | Sync then write. Only a tight race can be lost, that path is untested, and the lease is ignored (R1-1) |
| `state next counter` | yes | `t_state_next_counter` |
| `lease take` | partly | Matches the M2 table, but v1's single winner is not enforced (R1-3), and a lost acknowledgement is misreported (R1-11) |
| `lease check` | yes | `t_lease_take_race`: exit 0 or 5, holder printed |
| Machine block: one block, single-line values, unknown keys kept | partly | `t_state_set_and_get`. Unicode line separators split a value (R1-9) |
| Preflight: push access | yes | `t_preflight_push_access` |
| Preflight: `main` has commits | yes | `t_preflight_on_empty_repo` suggests `state init` to the architect |
| Preflight: approving reviews; 404 and 403-upgrade mean none | yes | `t_preflight_approving_reviews`: classic, ruleset, upgrade, other 403 |
| Preflight: admin bypass, report only | yes | `t_preflight_approving_reviews` |
| Preflight: `delete_branch_on_merge` | yes | `t_preflight_delete_branch_on_merge` |
| Preflight: state branch has PLAYBOOK.md, DESIGN.md and `pipeline: v…` | partly | A value that isn't a tag only warns, and local edits pass (R1-14, R1-15) |
| Preflight: lead-owned files, `--fix` | yes | `t_preflight_lead` |
| Preflight: ROOM_NTFY_TOPIC set; QODO_REVIEW on or off | yes | `t_preflight_lead`; the topic value is never printed |
| Preflight exits 0 only with no ✗ | yes | room.py:1068–1070 |

## Scope

Beyond the spec, the diff includes:

- docs: edits to BUILD-STATE.md (M0 done, milestones renamed, two new decisions) and the new `docs/design/m2-room-cli.md` itself;
- the playbook templates under `templates/playbook/`, which `state init` and `init-lead` need;
- a `ROOM_STATE_REMOTE` variable that sets the clone source;
- `read --from none`;
- `state init` also restores missing architect files and refuses a repo that has branches but no `main`;
- the role guard and the lease guard also apply to `close`;
- `state next` accepts any key;
- preflight adds a summary line and checks that MISSIONS.md parses;
- a non-tag `pipeline:` value is downgraded from ✗ to a warning (R1-15);
- the state tests live in a new `tests/test_state.py` with `tests/fake_gh_state.py`, instead of extending `tests/test_room.py`.

Every row of the spec's tables has an implementation. What is missing is behaviour that v1 requires and the M2 spec does not spell out: lease enforcement on state writes and a single lease winner (R1-1, R1-3), and a buzz for DONE when it is posted by `close` (R1-5). There are no tests for stale-lead writes or for a `state commit` rejection after a fetch. During the review the local branch moved to 5bf3ace. That commit touches only `docs/design/m3-reviews-gate.md`, which is excluded; room.py, the tests, the templates and the M2 spec are identical to c258e03.
