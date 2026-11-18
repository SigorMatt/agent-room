qodo: on
fetches: 1
reviewed: d9722dd16c67573f47c9e7f8d2e9aaf5273d1576

# Qodo dispositions, PR #16

| # | severity | finding | tags | file | disposition | Qodo now | cold caught |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Action required | Superseded holds can still permit merges | 🐞 Bug, ≡ Correctness | room.py | fixed in 09f8a88 | open | no |

- Fetches: 1, the first review, of d9722dd.
- Finding 1: the gate accepts a reason-5 decision only on the PR's newest hold: `MERGE-HOLD-<n> is not PR #<PR>'s newest hold: MERGE-HOLD-<m> came after it; use its DECISION`. So the clearing `DECISION` on an older hold never allows a merge, even when only records changed since its head (tests/test_m6f.py).
