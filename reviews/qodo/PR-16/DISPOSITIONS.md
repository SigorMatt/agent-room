qodo: on
fetches: 1, 2
reviewed: 12fde381dd46ef6d7788fdd6f2e8d38b8ec88af8

# Qodo dispositions, PR #16

| # | severity | finding | tags | file | disposition | Qodo now | cold caught |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Action required | Superseded holds can still permit merges | 🐞 Bug, ≡ Correctness | room.py | fixed in 09f8a88, c8f9a44, 2ef1e82 | resolved | no |

- Fetches: 1, the first review, of d9722dd; 2, of 12fde38, where finding 1 is resolved.
- Finding 1: the gate accepts a reason-5 decision only if no trusted lead hold for the PR came between its hold and it: `MERGE-HOLD-<m> came after MERGE-HOLD-<n> and before DECISION-<n>: answer MERGE-HOLD-<m> and use its DECISION`. A clearing `DECISION` on an older hold always comes after the newer hold, so it never allows a merge (first by content in 09f8a88 and c8f9a44, by room order since 2ef1e82, cold scoped-4 S4-1).
