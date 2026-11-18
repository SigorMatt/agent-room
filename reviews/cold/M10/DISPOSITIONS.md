# Cold dispositions, M6f

M6f's records are kept under `reviews/cold/M10/`, because the gate's exempt patterns name missions `M<digits>` (M6b's are under `M6`, M6d's under `M8`, M6e's under `M9`).

| ID | severity | file | finding | disposition | evidence |
| --- | --- | --- | --- | --- | --- |
| R1-1 | medium | room.py | Every `head <hex>` in a hold's text was checked, so a hold that also mentioned an older head (a supersedes note, a quoted refusal) never paired | fixed in 09f8a88, 38e6aff | The hold's head is the `head <hex>` that ends its first line, and nothing else counts; LEAD.md 5.6 step 5 puts other heads on a later line; tests in tests/test_m6f.py use cold's two_heads and supersedes scenarios |
| R1-2 | low | LEAD.md | Step 5 named no head source for a hold after `gate: PASS` (reasons 4 and 6) | fixed in 38e6aff | The head comes from a FAIL line's `(head …)`, or the first 12 digits of `gate: PASS <sha>` or `merge`'s `--sha` |
| R1-3 | low | room.py | `rev-parse <hex>^{commit}` lets a branch or tag named like the hex shadow the commit | fixed in 09f8a88 | The head resolves only as a commit-id prefix (`rev-parse --disambiguate`, exactly one commit); test with cold's tag_and_branch scenario |
| S1-1 | medium | room.py | The newest-hold check counted a later hold for any reason, so a reason-3, 4 or 6 hold after a reason-5 decision cancelled it, and its own decision couldn't allow the path | fixed in c8f9a44, f9ee084 | Only a later trusted lead `MERGE-HOLD` whose first line names the PR and `reason 5` supersedes; refusal `… is not PR #<PR>'s newest reason-5 hold …`; test with cold's reason3_after_merge scenario; LEAD.md 5.6 step 6, ARCHITECT.md 9.2, answer-a-buzz and troubleshooting say so |
| S1-2 | low | room.py | A period after the head made the hold count as naming no head | fixed in c8f9a44 | `head <hex>.` pairs; other trailing text still doesn't (tests in tests/test_m6f.py and tests/test_gate.py) |
