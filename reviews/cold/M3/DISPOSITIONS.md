# Cold dispositions, M3

| ID | severity | file | finding | disposition | evidence |
| --- | --- | --- | --- | --- | --- |
| R1-1 | high | templates/playbook/PLAYBOOK.md | Dependency and test globs match only root files | fixed in bbc16d3 | Globs prefixed `**/`, which matches zero or more segments; more manifests added; regression test |
| R1-2 | medium | room.py | `fixed in` accepts the reviewed commit, older commits, main commits, and any merge | fixed in b34aaac | Must come after the commit the finding was reported against, be off `origin/main`, and touch the file against its first parent; regression test |
| R1-3 | medium | room.py | Top-severity owner decisions need no DECISION in the room | fixed in 9de5b8f | A trusted `DECISION-<n>` must exist; regression test |
| R1-4 | medium | room.py | `--allow-hold` accepts any DECISION, unrelated to a hold of this PR | fixed in 9de5b8f | Needs the matching `MERGE-HOLD-<n>` naming `PR #<PR>`, `reason 5` and every matched path; spec updated (0c66593); regression test |
| R1-5 | medium | room.py | Qodo findings absent from the latest fetch need no row | fixed in 6cfa525 | Every title of every archived fetch needs a row; regression test |
| R1-6 | medium | room.py | An archive covers code even when its findings were never decided | fixed in ce5afb8 | An archive requires `qodo: on`, and covers only then; regression test |
| R1-7 | medium | room.py | Header counts and parsed findings may disagree silently | fixed in 6cfa525 | Disagreement fails: "Qodo comment did not parse: read it"; regression test |
| R1-8 | medium | room.py | `--mission` overrides the head ref's mission | fixed in 25e7c4b | Must agree with a mission token in the head ref; regression test |
| R1-9 | medium | room.py | Check runs collapsed by name hide a failure | fixed in 9af947d | Keyed by check suite and name; regression test |
| R1-10 | medium | room.py | CI that hasn't started reads as "no checks" | fixed in 9af947d | With workflows and no runs, WAIT while HEAD is under 10 minutes old; regression test |
| R1-11 | medium | room.py | Globs on wrapped bullet lines are dropped | fixed in bbc16d3 | Continuation lines are read; regression test |
| R1-12 | low | room.py | A blank line ends a findings table | fixed in 2912ec2 | Tables continue across blank lines; regression test |
| R1-13 | low | room.py | Badges quoted in code excerpts relabel severities | fixed in 423e67a | Badges inside code are ignored; regression test |
| R1-14 | low | room.py | Findings sharing a title take the last severity | fixed in 423e67a | The strictest severity wins; regression test |
| R1-15 | low | room.py | Titles with `<…>` never match their row | fixed in 423e67a | Both sides unescaped and folded the same way; regression test |
| R1-16 | low | room.py | Merged PR with a failed state update exits 5 | fixed in 910d8b6 | Exits 1 with "merged …; state not updated …: reconcile"; regression test |
| R1-17 | low | room.py | A deferral may cite any ledger row | fixed in 19dfc98 | Needs an open row with the same target and a source naming the finding; regression test |
