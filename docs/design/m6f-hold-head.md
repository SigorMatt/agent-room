# M6f spec: a hold's decision is bound to the head the hold showed (B-11)

Builds backlog item B-11 before v1.0.0, as Matthew decided on 2026-11-18. Same constraints as M2: standard-library Python, `gh` and `curl` only.

## The problem

Since M3, `gate` and `merge` with `--allow-hold 5 --decision DECISION-<n>` accept a `DECISION-<n>` when it answers the lead's `MERGE-HOLD-<n>` for the same PR, reason 5 and paths (`check_sensitive`). They don't check which code the hold showed.

A lead that holds, goes back to Build after another decision, changes a held path and holds again leaves the older hold open. Answering the older hold then merges code it never showed (cold M6e scoped-5 S5-2, scoped-6 S6-2 and S6-3, scoped-7 S7-1 and S7-2).

## The rule

**A hold names its head.** Every `MERGE-HOLD`'s first line ends with `, head <sha>`: the PR head the gate checked, at least 12 hex digits (LEAD.md 5.6 step 5 prints 12), taken from the gate's `FAIL` line, its `PASS <sha>` line, or `merge`'s `--sha` (cold M6f R1-2). Holds for reasons other than 5 name it too. Only that trailing head counts: other heads mentioned in the hold, an older hold's say, are ignored (cold M6f R1-1). Only reason 5 is checked by the gate, but the architect reads the head for every hold.

**The gate checks it.** With `--allow-hold 5 --decision DECISION-<n>`, the pair that `check_sensitive` finds (a whole hold before the decision) must also pass these checks, against the head being gated:

1. **It names a head.** The hold's first line ends with `head <hex>`, 12 to 40 hex digits, optionally followed by a period (cold M6f scoped-1 S1-2). `hold_problems` reports a missing head alongside a missing PR, reason or path, so the "the form:" line names it.
2. **The head is in this PR's history.** It resolves as a commit-id prefix, never through a ref name (cold M6f R1-3), to exactly one commit, and that commit is an ancestor of the gated head. If either fails, refuse: `MERGE-HOLD-<n> names head <hex>, which isn't in PR #<PR>'s history: post a new hold for head <head12>`.
3. **Only review records changed since.** Every path changed between the hold's head and the gated head (`git diff --name-only <hold head> <head>`) must be a review record (`exempt(path)`, the coverage rule's `REVIEW_EXEMPT`). The decision's own record push, section 9 step 3's rows, moves the head after the hold, and that must still pass (cold M6e scoped-6 S6-2). If any other path changed, refuse: `MERGE-HOLD-<n> was posted for head <hold12>; PR #<PR> changed since (<up to 5 paths, then "and N more">): post a new hold for head <head12>`.

4. **It is the PR's newest reason-5 hold.** No trusted lead `MERGE-HOLD` whose first line names the same PR and `reason 5` comes after it in the room. A later hold for another reason only (3, 4 or 6, say after a 405) doesn't supersede the reason-5 decision (cold M6f scoped-1 S1-1). Only the newest hold's decision can allow a merge, so a clearing `DECISION` on an older hold ("superseded", allowing nothing) never does, even when only records changed since its head (qodo PR #16 finding 1). Refusal: `MERGE-HOLD-<n> is not PR #<PR>'s newest hold: MERGE-HOLD-<m> came after it; use its DECISION`.

The refusal is reason 5, like the existing failures in `check_sensitive`, so the lead holds again (5.6 step 5) for the current head. A hold that fails 1 to 3 never pairs. If no hold pairs, the existing "no trusted DECISION / no MERGE-HOLD" messages stay, except that the most specific failure from 1 to 3 is reported when one exists.

**The head in the verdict.** `gate: FAIL hold reasons …` adds `(head <head12>)` at the end, so the lead copies the head into its hold from the same output. The `gate: FAIL hold reasons` prefix is kept, and so is `gate: PASS <head>`.

**Old holds.** A hold posted before M6f names no head, so its decision no longer allows a merge. The lead holds again. No room in flight has an open reason-5 hold today: pet-todo's phases are done.

## Docs

- **`LEAD.md` 5.6 step 5:** the hold's form ends with `, head <head12>`, copied from the gate's `FAIL` line. Step 6 is unchanged; the gate does the check.
- **`ARCHITECT.md` 9.2:** every hold names its head. When several holds for one PR are open, answer the newest. Before Matthew answers it, show him what changed on its held paths since the older hold: `git diff <older head> <newer head> -- <held paths>`. An empty diff means it's the same code, which covers B-10's record-only re-hold (cold M6e scoped-7 S7-1, S7-2). Clear the older hold with a `DECISION` that allows nothing. The gate refuses an older hold's decision at a newer head anyway. Keep it short.
- **Manuals:**
  - `answer-a-buzz` (the `MERGE-HOLD` entry): the head, and the several-holds rule.
  - `message-kinds`: the form.
  - `troubleshooting`: the two new refusals.
  - `glossary`, if it defines a hold.
- **`CHANGELOG.md`.**
- **`BUILD-STATE.md`:** B-11 done in M6f, and an M6f milestone row.

## Tests

All offline, in a new `tests/test_m6f.py`, or in `tests/test_gate.py` if its harness fits better:
- A decision at the hold's own head: pass.
- At a later head where only review records changed: pass.
- At a later head where another path changed: refused, naming the path and both heads.
- A hold head that isn't an ancestor of the gated head (a force push), and one that doesn't resolve: refused.
- A hold with no head: no pair, and the form names `head`.
- An older hold's decision when a newer hold for the same PR exists, even with only records changed between their heads: refused, naming the newer hold.
- A hold that mentions an older head on a later line, or quotes a refusal: its trailing first-line head counts.
- A ref named like the head hex doesn't shadow the commit.
- B-11's scenario: `MERGE-HOLD-37` at H1, then a held path changes and `MERGE-HOLD-38` at H2. `DECISION-37` at H2 is refused, and `DECISION-38` at H2 passes.
- The `FAIL` verdict names the head; the `PASS` verdict is unchanged.
- `merge --allow-hold 5 --decision` behaves like `gate`.
