# Cold review M6f scoped 7
covers: 0863a0ac37e9242671df5ff07349752804c8cb90
base: 5d7142b8619bf2e5c91ec6c4d158bb5a2c62e2df
spec: docs/design/m6f-hold-head.md at 0863a0ac37e9242671df5ff07349752804c8cb90
since: 543ff4845cd1d563da3bc88920b610888f737ca7

## Findings

| ID | severity | file:line | finding | failure scenario |
| --- | --- | --- | --- | --- |

No findings.

## Scoped 6 fixes

| ID | holds | evidence |
| --- | --- | --- |
| S6-1 | yes | The comment at room.py:2580-2583 now says the pair needs "no lead MERGE-HOLD of any PR posted between that hold and the decision (hold_between: room order only; a hold after the decision doesn't cancel it)". That matches `hold_between` (room.py:2476-2484): it filters by id range, role `lead` and base kind `MERGE-HOLD` only. It also matches spec rule 4 (m6f-hold-head.md:21-25). A probe (/tmp/cold-m6f-s7/scripts/probe.py, logs/probe.log) checked the comment's wording against `hold_between` in 8 cases, and all 8 agree. These count as a hold between: one for PR #13, one for reason 3, one with no PR or head, and one edited after the decision. These don't: a hold posted after the decision (also with an earlier timestamp), an architect-tagged `MERGE-HOLD`, and a lead `STATUS` naming a hold. Spec :36 now says what ARCHITECT.md:366 and answer-a-buzz.md:45 say: answer the newest; a decision posted after a newer hold, for any PR, never allows; a later hold doesn't cancel. Spec :53 now matches the tests. `t_a_hold_between_the_hold_and_its_decision` and `t_another_prs_hold_between_refuses_by_design` refuse with the newer hold named. `t_a_rehold_after_the_decision` and `t_a_later_hold_for_another_reason` pass a decision posted before a newer hold. Both S6-1 scenarios now read the same in the comment, the spec and the code. No code changed: the ASTs of room.py at 3c2bf12^ and 3c2bf12 are identical, and the diff is 3 comment lines. `tests/test_m6f.py` passed (all 19 tests, logs/test_m6f.log), and so did `tests/test_docs.py` (6 tests, logs/test_docs.log). The BUILD-STATE row changes only "6 scoped reviews" to "7". That follows the row's history: each fix commit counts the scoped review that follows it (2f7b8ae through 937af42). |

## Scope

I read `git show 3c2bf12` in full, then the whole spec. In room.py I read `hold_between`, `RoomLog.messages`, `before`, `answers`, `holds`, `hold_head`, `hold_problems`, `hold_head_problem` and all of `check_sensitive`. I also read every test in tests/test_m6f.py, scoped-6.md, DISPOSITIONS.md, the BUILD-STATE M6f and B-11 rows with the M6f row's history, ARCHITECT.md 9.2, LEAD.md 5.6 steps 5 and 6, answer-a-buzz.md:45, troubleshooting.md:53-56 and CHANGELOG.md:23. I searched room.py, LEAD.md, ARCHITECT.md, CHANGELOG.md, the manuals and the spec for older wording ("for this PR after", "same PR", "newest reason-5", "supersede", "newer hold", "older hold"). Apart from the problem statement at spec :7, which describes behaviour before M6f, none remains. Four things I looked at don't count as findings. (1) Spec :36 keeps "The gate refuses an older hold's decision at a newer head anyway" from c1ec65b, written before check 4. It is still true for the holds the line is about. An open older hold's decision can only be posted after the newer hold, so check 4 refuses it at any head. "at a newer head" is now only narrower than it needs to be. (2) Spec :36's "never allows a merge" is wider than check 4, which runs only with `--allow-hold 5`. A reason-1 owner decision goes through `RoomLog.answers`, which has no between check. But that path relies on the lead copying the decision's words into the row (`owner decision: <text>, Matthew (DECISION-n)`), so a clearing "superseded" decision gives a row nothing to cite. ARCHITECT.md:366 has said the same since before 3c2bf12. (3) The unchanged comment text at room.py:2581 ("a head whose code is HEAD's but for review records") doesn't mention check 2's ancestry rule. It came from 52f3f48 and is outside this diff. Dropping ancestry for identical code would still leave check 3 binding the tree. (4) The pre-counted "7 scoped reviews" is explained above. Throwaway files are only under /tmp/cold-m6f-s7/ (scripts/probe.py, room_before.py, room_after.py, logs/). Nothing in the repo was edited, committed or pushed.
