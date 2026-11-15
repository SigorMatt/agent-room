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

- `LEDGER.md` table: `| ID | source | finding | reason | target | status |`. ID `L-<n>`; source `cold M3 R1-2` (mission and finding ID) or `qodo PR #12`, with the Qodo finding's title, as the tool prints it, in the source or the finding column; target `M<k>` or `phase <p> backlog`; status `open`, `fixed in <sha>`, `deferred again: L-<m>` or `won't fix (Matthew, DECISION-<n>)`.
- `QODO-VALUE.md`: one line per PR, in the format of the example in `v1.md`.

The M2 templates under `templates/playbook/` are aligned to these formats in this mission if they differ.

## `room.py gate PR [--mission M<k>] [--allow-hold 5 --decision DECISION-<n>]`

Run by the lead in the project checkout. Prints one line per check (`✓`/`✗`, with the reason), then a verdict line.

1. **PR:** read `pulls/<PR>`: open, base `main`, head ref `mission/M<k>-…` (the mission is the token right after `mission/`; `--mission`, if given, must equal it). `git fetch origin <head ref> main`; the fetched head must equal the PR's head sha. All later checks use that sha, called HEAD here.
2. **Lease:** `lease check` passes.
3. **Coverage:** collect the covered commits: every cold report's `covers:` and, when the Qodo dispositions file says `qodo: on`, the reviewed commit of the latest Qodo archive of this PR (its Code Review comment's commit marker). Passes when some covered commit X is an ancestor of HEAD (or equal), and `git diff --name-only X HEAD` has no path outside the exempt set. Otherwise lists the uncovered paths.
4. **Dispositions:**
    - the cold dispositions file exists and has a row for every finding ID in every cold report;
    - when `QODO_REVIEW=on`, the Qodo dispositions file exists. When an archive of this PR exists, the file exists and its `qodo:` is `on`, whatever `QODO_REVIEW` says;
    - with `qodo: on`, it has a row for every finding title of every archived fetch of this PR, absent-now ones included. Titles are compared after unescaping entities and folding case and whitespace, the archive's title as the tool prints it (markup and the resolved mark removed), the table cell as written. A title's severity is the strictest any finding of that title had in any fetch; severity badges inside code (`<pre>`, `<code>`, fenced blocks) don't count;
    - the archive is whole: its fetch directories are numbered 1 to k, as the tool numbers them, and equal the `fetches:` line, and `reviewed:` names the last fetch's reviewed commit (backticks stripped, a hex prefix of 7 or more characters, text after the sha ignored). Otherwise the lead fixes the records first;
    - `QODO-REVIEW.md` rule 5: in every archived Code Review comment, the header's open count must equal the open findings that parse, and every finding has a known severity. Otherwise "Qodo comment did not parse: read it" or "severity did not parse: read the comment". The records can't fix either: Qodo's format moved, and room.py's parser needs a patch;
    - every row's disposition parses, and top severity rows use only the allowed forms. An `owner decision … (DECISION-<n>)` on a top-severity row needs a trusted `DECISION-<n>` in the room (from the architect, or untagged from Matthew) posted after the lead's trusted `ESCALATION-<n>` or `MERGE-HOLD-<n>` that names the finding: its cold ID, the full Qodo title, or the path of the dispositions file it sits in (`reviews/cold/M<k>/DISPOSITIONS.md` or `reviews/qodo/PR-<n>/DISPOSITIONS.md`); otherwise it is an open owner decision;
    - `fixed in <sha>`: the sha is an ancestor of HEAD, is not on `origin/main`, and is not an ancestor of (or equal to) the commit the finding was reported against: the `covers:` of the cold report that holds it, or the reviewed commit of the first Qodo fetch that shows the finding open. When no fetch shows it open, any commit of the PR that is off `main` and touches the file passes. When a file is given, the commit's diff against its first parent touches it, so a lead's merge of a builder branch counts for what it brought in;
    - `deferred: L-<n> to <target>`: the target is later than this mission: `M<j>` with `j` above this mission's number, or `phase <p> backlog` with `p` above the current phase in `MISSIONS.md`. `LEDGER.md` on the state branch has row `L-<n>` with status `open`, the same target, and a source naming this finding (the mission and cold ID, or `PR #<n>` and the title);
    - an open owner decision or an undecided row fails with hold reason 1 or 2.
5. **Checks:** check runs (`filter=latest`, told apart by check suite and name) and commit statuses on HEAD. Required contexts come from `main`'s protection and rulesets (404 or the upgrade 403: none). Fails if a required context is missing or not successful, or any completed run failed (hold reason 3). Pending runs give the wait verdict, and so does a required context that hasn't reported while another check is still pending, until 60 minutes after the later of HEAD's committer date and the PR's `updated_at`; then the missing context fails (hold reason 3). If HEAD's tree has `.github/workflows/*.y*ml` and HEAD has no GitHub Actions check run (app `github-actions`; other apps' runs and statuses don't count), the gate waits for 10 minutes from the later of HEAD's committer date and the PR's `updated_at`, then judges what is there, noting "no checks ran for HEAD" when nothing is. Without workflow files, no checks at all passes as "no checks configured". A missing required context fails once nothing is pending and the wait is over.
6. **Sensitive paths:** the changed paths (`git diff --name-status origin/main...HEAD`) against the globs of the "## Merge-hold list" section of `PLAYBOOK.md` on the state branch. The template has one bullet per area, ``- <label>: `glob`, `glob` ``; every backticked glob in a bullet counts, including globs on indented continuation lines. A glob that starts or ends with `/` can never match a changed path and fails as such. `*` matches within a path segment, `**` across segments, and `**/` any number of directories, none included (`**/go.mod` matches `go.mod` and `lib/go.mod`). Matching ignores case. A bullet whose label contains "deleted" (any case) matches only deleted paths, so adding or editing tests never holds; weakened tests are the cold reviewer's to flag. A match fails with hold reason 5, naming the path and the glob, unless `--allow-hold 5 --decision DECISION-<n>` is given and the room holds both a trusted `DECISION-<n>` (from the architect, or untagged from Matthew) posted after the lead's trusted `MERGE-HOLD-<n>`, with the same `n`, whose text names `PR #<PR>`, `reason 5` and every matched path, each as a whole token: backticked, or a word split on whitespace and commas, with quotes, a trailing `.`, `,`, `;` or `:` and unbalanced parentheses dropped (so `src/app/(auth)/page.tsx` can be named). The lead posts the hold in this form; a failing gate names the missing message, and when a hold exists but doesn't name everything it prints this form with the number left as `<n>`, which is safe because the decision must still come after the hold:

    ```text
    MERGE-HOLD-<n>: PR #<PR>, reason 5 (sensitive paths): <path>, <path>, …
    ```

    A decision therefore allows only the hold it answers: another PR, another reason or another path needs its own hold and decision. A playbook with no merge-hold section, or one with no globs, fails: the gate never runs without the list.

**Verdict and exit:**
- `gate: PASS <HEAD sha>`: exit 0.
- `gate: WAIT <reason>` (checks pending): exit 3.
- `gate: FAIL hold reasons <list>`: exit 6. Hold reasons as numbered in `v1.md`; scope (4) and missing Qodo reviews (6) are the lead's, not the gate's.
- Lease lost: exit 5. Errors: exit 1.

## `room.py merge PR --sha SHA [--allow-hold … --decision …]`

1. Runs the gate; it must pass with HEAD equal to `SHA`.
2. `state set intent="merge PR #<PR> at <SHA>"`.
3. `gh api -X PUT repos/O/N/pulls/<PR>/merge -f sha=<SHA> -f merge_method=merge`. A merge commit keeps every `fixed in` sha reachable from `main` after the branch is deleted.
4. On success: `state set intent=none pr=merged:<PR>`; prints `merged PR #<PR>: <merge sha>`; exit 0. If that state update fails (lease lost, the branch moved): prints `merged PR #<PR>: <merge sha>; state not updated (<why>): reconcile`, exit 1, intent left recorded. On 409 (head moved): exit 3 with `head moved: re-run gate`. On 405 (not mergeable): exit 6. Other errors: exit 1, intent left recorded for reconciliation.

## Agent-room deviations in `docs/QODO-REVIEW.md`

Insert a short section right after the "For the session" paragraph, headed "In agent-room", listing the four deviations of `v1.md` and pointing to this file for the record formats. The appendix and its markers stay byte-identical, so the extraction command keeps working; a test extracts the tool from the doc and compiles it.

## Tests

`tests/test_gate.py`, with the fake `gh` extended for check runs, statuses, PR objects and the merge endpoint (200, 405, 409), and a local bare remote for the mission and state branches. Cover each check's pass and fail, every disposition form including top-severity misuse, coverage with a record-only commit after the last review, an uncovered file under `reviews/`, a deleted test file, `--allow-hold` with and without a matching decision, merge success, 409 and 405, and the doc extraction.

## Changes after cold review

Each fix has a regression test in `tests/test_gate.py`.

### Round 1

`reviews/cold/M3/round-1.md` found 17 holes in the first implementation.

- R1-1, R1-11: the template's dependency and test globs start with `**/`, which matches no directory as well as many; globs on a bullet's continuation lines count.
- R1-2: `fixed in` must name a commit after the review that found the finding, off `main`, and touches files by its first-parent diff.
- R1-3, R1-4: a top-severity owner decision needs the room's `DECISION-<n>`; `--allow-hold 5` needs that decision to answer the lead's `MERGE-HOLD-<n>` for this PR, reason 5 and its paths.
- R1-5, R1-14, R1-15: Qodo rows cover every archived fetch, at each title's strictest severity, with titles compared as written.
- R1-6: an archived Qodo review requires `qodo: on`, and covers code only then.
- R1-7: rule 5 of `QODO-REVIEW.md` (counts must agree) is enforced.
- R1-8: `--mission` must match the head ref.
- R1-9, R1-10: check runs are keyed by suite and name; a new HEAD with workflows and no runs waits.
- R1-12, R1-13: a blank line inside a table doesn't end it; badges inside code aren't severities (`qodo_review.py` has the same weakness).
- R1-16: a merge whose state update fails exits 1 with the reconcile message.
- R1-17: a deferral needs its own open ledger row with the same target.

### Round 2

`reviews/cold/M3/round-2.md` found 12 more. The gate is a mechanical aid for a cooperative lead, not a defence against a hostile one, so each fix is small. R2-4 was dismissed: v1 says Qodo's marks don't count, and a reopened finding is handled at triage.

- R2-1, R2-10: the `DECISION-<n>` that allows a hold is posted after the `MERGE-HOLD-<n>`; hold paths match as whole tokens; a failing gate names the missing message instead of printing hold text.
- R2-2: a top-severity owner decision answers the lead's earlier `ESCALATION-<n>` or `MERGE-HOLD-<n>` naming the finding.
- R2-3: a Qodo fix is bounded by the first fetch showing the finding open, or only by the PR's own commits when none does.
- R2-5, R2-9: the Qodo archive runs 1..k and matches `fetches:` and `reviewed:`; a finding without a known severity fails; parse failures say a parser patch is the fix.
- R2-6: with workflow files, the gate waits for GitHub Actions runs, timed from the later of HEAD's commit and the PR's last update; a late required context waits while others run.
- R2-7: the template's merge-hold list covers common auth, crypto, secret, migration, manifest, lock-file and test layouts.
- R2-8: `--mission` must equal the mission right after `mission/`.
- R2-11: a glob starting or ending with `/` fails as one that can never match.
- R2-12: a deferral targets a later mission or a later phase's backlog.

### Scoped review 1

`reviews/cold/M3/scoped-1.md` reviewed the round-2 fixes. S1-4 was dismissed: over-holding is the safe direction and v1 makes the list editable per project; the template now says so to the architect.

- S1-1: merge-hold globs ignore case, and the template holds `security` and `account` code, credentials, `.env` files and key stores.
- S1-2: hold paths may contain parentheses and trailing punctuation; a hold that misses a path gets the form printed with `<n>`.
- S1-3: an escalation or hold may name a finding by the path of its dispositions file.
- S1-5: a required context unreported while others run holds after 60 minutes.
- S1-6: the `reviewed:` line is normalised before it is compared.
