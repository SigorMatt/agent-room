# M3 spec: review records, `room.py gate` and `room.py merge`

Implements the "Reviews, dispositions and the ledger", "Qodo" and "Merge gate" sections of `v1.md`. Where the two differ, `v1.md` plus `BUILD-STATE.md` decisions win, and this file gets fixed. Same constraints as M2: one file, standard library, Python 3.9+, GitHub only through `gh` and `git`.

## Review records

All records live on the mission branch under `reviews/` and are the only files the coverage rule exempts. The exempt set is exactly these patterns (deferral B-1); anything else under `reviews/` counts as a change needing review:

| Pattern | What |
| --- | --- |
| `reviews/cold/M<k>/round-<r>.md` | A cold review round, `r` = 1 or 2 |
| `reviews/cold/M<k>/scoped-<s>.md` | A scoped cold review, `s` = 1, 2, … |
| `reviews/cold/M<k>/DISPOSITIONS.md` | Dispositions of every cold finding |
| `reviews/qodo/PR-<n>/DISPOSITIONS.md` | Dispositions of every Qodo finding |
| `reviews/qodo/PR-<n>/<k>/(issue-comment\|review\|review-comment)-<id>.(md\|json)` | Qodo archives written by `qodo_review.py` |

`<k>`, `<r>`, `<s>`, `<n>`, `<id>` are decimal numbers. Matching is on the whole path.

### Cold review report

`reviews/cold/M<k>/round-<r>.md` or `scoped-<s>.md`. The first lines are machine lines, then free text:

```markdown
# Cold review M3 round 1
covers: <40-hex sha of the mission branch head that was reviewed>
base: <40-hex sha of main it was diffed against>
spec: <state-branch commit the spec was pinned at>
since: <40-hex sha>            # scoped reviews only: the last covered commit

## Findings

| ID | severity | file:line | finding | failure scenario |
| --- | --- | --- | --- | --- |
| R1-1 | high | room.py:120 | … | … |

## Criteria

| criterion | met | evidence |
| --- | --- | --- |
| P1.2 | yes | test_x |

## Scope

Inside the spec / outside the spec: one paragraph.
```

- IDs: `R<r>-<n>` for rounds, `S<s>-<n>` for scoped reviews. Severity: `high`, `medium` or `low`.
- A report with no findings keeps the table header and says "none" under it.

### Cold dispositions

`reviews/cold/M<k>/DISPOSITIONS.md`: one row per finding ID of every round and scoped report.

| ID | severity | file | finding | disposition | evidence |
| --- | --- | --- | --- | --- | --- |

### Qodo dispositions

`reviews/qodo/PR-<n>/DISPOSITIONS.md`, as `QODO-REVIEW.md` step 7 plus the `cold caught` column (deviation 2), preceded by machine lines:

```markdown
qodo: on | off | no first review
fetches: 1, 2, 3
reviewed: <40-hex sha of the last fetch's reviewed commit>
no re-review: <sha>, …          # optional

| # | severity | finding | tags | file | disposition | Qodo now | cold caught |
| --- | --- | --- | --- | --- | --- | --- | --- |
```

With `qodo: off` or `qodo: no first review`, the table may be empty.

### Disposition grammar

Both tables use the same grammar in the `disposition` column:

| Form | Allowed for top severity (`high`, `Action required`) |
| --- | --- |
| `fixed in <7–40 hex sha>` | yes |
| `dismissed: <reason>` | no |
| `deferred: L-<n> to M<k>` or `deferred: L-<n> to phase <p> backlog` | no |
| `owner decision: <what>, Matthew (DECISION-<n>)` | yes |
| `owner decision: pending (ESCALATION-<n>)` | an open owner decision: hold reason 1 |

Anything else, or an empty cell, is undecided.

### Ledger and value files (state branch)

- `LEDGER.md` table: `| ID | source | finding | reason | target | status |`. ID `L-<n>`; source like `cold M3 R1-2` or `qodo PR #12 #3`; target `M<k>` or `phase <p> backlog`; status `open`, `fixed in <sha>`, `deferred again: L-<m>` or `won't fix (Matthew, DECISION-<n>)`.
- `QODO-VALUE.md`: one line per PR, in the format of the example in `v1.md`.

The M2 templates under `templates/playbook/` are aligned to these formats in this mission if they differ.

## `room.py gate PR [--mission M<k>] [--allow-hold 5 --decision DECISION-<n>]`

Run by the lead in the project checkout. Prints one line per check (`✓`/`✗`, with the reason), then a verdict line.

1. **PR:** read `pulls/<PR>`: open, base `main`, head ref `mission/M<k>-…` (the mission comes from it unless `--mission`). `git fetch origin <head ref> main`; the fetched head must equal the PR's head sha. All later checks use that sha, called HEAD here.
2. **Lease:** `lease check` passes.
3. **Coverage:** collect the covered commits: every cold report's `covers:` and the reviewed commit of the latest Qodo archive of this PR (its Code Review comment's commit marker). Passes when some covered commit X is an ancestor of HEAD (or equal), and `git diff --name-only X HEAD` has no path outside the exempt set. Otherwise lists the uncovered paths.
4. **Dispositions:**
    - the cold dispositions file exists and has a row for every finding ID in every cold report;
    - when `QODO_REVIEW=on`, the Qodo dispositions file exists; when its `qodo:` is `on`, it has a row for every finding title in the latest archived Code Review comment (titles compared as plain text, case-folded, markup and the resolved mark removed);
    - every row's disposition parses, and top severity rows use only the allowed forms;
    - `fixed in <sha>`: the sha is an ancestor of HEAD and the commit touches the row's file when one is given;
    - `deferred: L-<n> …`: `L-<n>` exists in `LEDGER.md` on the state branch;
    - an open owner decision or an undecided row fails with hold reason 1 or 2.
5. **Checks:** check runs and commit statuses on HEAD. Required contexts come from `main`'s protection (404 or the upgrade 403: none). Fails if a required context is missing or not successful, or any completed run failed (hold reason 3). Pending runs give the wait verdict. No checks at all passes, noted as "no checks configured".
6. **Sensitive paths:** the changed paths (`git diff --name-status origin/main...HEAD`) against the globs of the "## Merge-hold list" section of `PLAYBOOK.md` on the state branch. The template has one bullet per area, ``- <label>: `glob`, `glob` ``; every backticked glob in a bullet counts. `*` matches within a path segment, `**` across segments. A bullet whose label contains "deleted" (any case) matches only deleted paths, so adding or editing tests never holds; weakened tests are the cold reviewer's to flag. A match fails with hold reason 5, naming the path and the glob, unless `--allow-hold 5 --decision DECISION-<n>` is given and the room holds a trusted architect comment whose kind is that `DECISION-<n>`. A playbook with no merge-hold section, or one with no globs, fails: the gate never runs without the list.

**Verdict and exit:**
- `gate: PASS <HEAD sha>`: exit 0.
- `gate: WAIT <reason>` (checks pending): exit 3.
- `gate: FAIL hold reasons <list>`: exit 6. Hold reasons as numbered in `v1.md`; scope (4) and missing Qodo reviews (6) are the lead's, not the gate's.
- Lease lost: exit 5. Errors: exit 1.

## `room.py merge PR --sha SHA [--allow-hold … --decision …]`

1. Runs the gate; it must pass with HEAD equal to `SHA`.
2. `state set intent="merge PR #<PR> at <SHA>"`.
3. `gh api -X PUT repos/O/N/pulls/<PR>/merge -f sha=<SHA> -f merge_method=merge`. A merge commit keeps every `fixed in` sha reachable from `main` after the branch is deleted.
4. On success: `state set intent=none pr=merged:<PR>`; prints `merged PR #<PR>: <merge sha>`; exit 0. On 409 (head moved): exit 3 with `head moved: re-run gate`. On 405 (not mergeable): exit 6. Other errors: exit 1, intent left recorded for reconciliation.

## Agent-room deviations in `docs/QODO-REVIEW.md`

Insert a short section right after the "For the session" paragraph, headed "In agent-room", listing the four deviations of `v1.md` and pointing to this file for the record formats. The appendix and its markers stay byte-identical, so the extraction command keeps working; a test extracts the tool from the doc and compiles it.

## Tests

`tests/test_gate.py`, with the fake `gh` extended for check runs, statuses, PR objects and the merge endpoint (200, 405, 409), and a local bare remote for the mission and state branches. Cover each check's pass and fail, every disposition form including top-severity misuse, coverage with a record-only commit after the last review, an uncovered file under `reviews/`, a deleted test file, `--allow-hold` with and without a matching decision, merge success, 409 and 405, and the doc extraction.
