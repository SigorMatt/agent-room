qodo: on
fetches: 1, 2
reviewed: 12fde381dd46ef6d7788fdd6f2e8d38b8ec88af8

# Qodo dispositions, PR #16

| # | severity | finding | tags | file | disposition | Qodo now | cold caught |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Action required | Superseded holds can still permit merges | 🐞 Bug, ≡ Correctness | room.py | fixed in 09f8a88, c8f9a44 | resolved | no |

- Fetches: 1, the first review, of d9722dd; 2, of 12fde38, where finding 1 is resolved.
- Finding 1: the gate accepts a reason-5 decision only on the PR's newest reason-5 hold: `MERGE-HOLD-<n> is not PR #<PR>'s newest reason-5 hold: MERGE-HOLD-<m> came after it; use its DECISION` (narrowed to reason-5 holds in c8f9a44, cold scoped-1 S1-1). So the clearing `DECISION` on an older hold never allows a merge, even when only records changed since its head (tests/test_m6f.py).
