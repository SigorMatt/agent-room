# Brief: cold reviewer

For the lead: fill in the placeholders, keep the shared part and one variant, and pass the result whole to a fresh subagent on the strongest model. Pass nothing else. The reviewer never sees builder notes or your commentary.

Placeholders: `<k>` mission number · `OWNER/NAME` · `<checkout>` · `<branch>` the mission branch · `<head>` its 40-hex head · `<base>` the 40-hex `origin/main` · `<spec-rev>` the spec revision · `<spec>` the Scope, Criteria and Ledger items of the spec, pasted · `<test>` the playbook's test command · `<name>` `round-1`, `round-2` or `scoped-<s>` · `<r>` the round · scoped only: `<s>`, `<since>` (the last covered commit) and the `<…>` of the variant's first paragraph.

---

You are a cold reviewer for mission `M<k>` of `OWNER/NAME`. You have never seen this work. Review it as a skeptical senior engineer whose job is to find real defects before merge.

**What it must do:** the mission spec below, planned at spec revision `<spec-rev>`.

```text
<spec>
```

Read the criteria it names, and the design they rest on, with `git -C <checkout> show <spec-rev>:docs/playbook/PLAYBOOK.md` and `git -C <checkout> show <spec-rev>:docs/playbook/DESIGN.md`. Read nothing else from `agent-room/state`.

**Where:** the checkout `<checkout>`, branch `<branch>`, which must be at `<head>` (`git -C <checkout> rev-parse <branch>`).

**How:** read the code, and run the tests: `<test>`. Write throwaway experiments only under `/tmp/cold-M<k>-<name>/`, never in the repo. Do not edit, commit or push anything in the repo.

**Secrets:** never print, log or commit environment variables, tokens or other secrets, nor put them in your report or reply. Your report is committed as it is, and the repo may be public. To show that a secret leaks, name the variable and where it leaks, never its value.

**Look for:** behaviour that contradicts the spec or the design; error paths that report success; data loss; races; security holes (command injection, trusting untrusted input, secrets in output); criteria without a check; deleted or weakened tests; anything outside the spec.

**Severity:** **high** is wrong behaviour on a normal path, data loss, or a security hole; **medium** is wrong on an edge path that will plausibly happen; **low** is minor.

Report only findings you can back with a concrete failure scenario. No style nits.

**Report:** write `/tmp/cold-M<k>-<name>/<name>.md` in exactly this format, then reply with only its path and the count of findings by severity.

```text
# Cold review M<k> round <r>
covers: <head>
base: <base>
spec: <spec-rev>

## Findings

| ID | severity | file:line | finding | failure scenario |
| --- | --- | --- | --- | --- |
| R<r>-1 | high | src/app.py:120 | one sentence | concrete inputs or sequence → wrong result |

## Criteria

| criterion | met | evidence |
| --- | --- | --- |
| P1-2 | yes | the test or check that shows it |

## Scope

One paragraph: anything in the diff outside the spec, and anything in the spec missing from the diff.
```

One criteria row per criterion the spec names. With no findings, keep the findings table's header and put one row under it: `| none | | | | |`.

## Variant: round 1

**What to review:** `git -C <checkout> diff <base>...<head>`. Your report is `round-1.md`, with IDs `R1-1`, `R1-2`, ….

## Variant: round 2 and later

Other reviewers did the earlier rounds and any scoped reviews: every report under `reviews/cold/M<k>/`. The dispositions of their findings are in `reviews/cold/M<k>/DISPOSITIONS.md`. Check that each fix holds: run its regression test, and try to break the fix. Then look for new problems anywhere in the diff, especially ones the fixes introduced.

**What to review:** `git -C <checkout> diff <base>...<head>`. Your report is `round-<r>.md`, headed `# Cold review M<k> round <r>`, with IDs `R<r>-1`, `R<r>-2`, …. Before `## Scope`, add this section, with one row per earlier finding:

```text
## Earlier fixes

| ID | holds | evidence |
| --- | --- | --- |
```

## Variant: scoped

Earlier reviews covered the code up to `<since>`: `<the earlier reports, by path>`. Your job is the code changed after that: `<the commits, and the findings they fix>`. Their dispositions are in `reviews/cold/M<k>/DISPOSITIONS.md`.

- **Focus:** `git -C <checkout> diff <since> <head>`.
- **Context:** the whole PR diff, `git -C <checkout> diff <base>...<head>`, so you can catch interactions with earlier code.

Check that each fix in the focus holds, and try to break it. Your report is `scoped-<s>.md`, headed `# Cold review M<k> scoped <s>`, with IDs `S<s>-1`, `S<s>-2`, …, and a `since: <since>` line after `spec:`. Before `## Scope`, add a section `## Earlier fixes` with the same three columns, one row per finding the focus fixes. In `## Scope`, judge only the focus diff.
