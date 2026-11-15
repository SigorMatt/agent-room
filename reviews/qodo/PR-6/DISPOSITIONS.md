qodo: on
fetches: 1, 2
reviewed: a7819374fe298f7392e483186191e470f51bce15

# Qodo dispositions, PR #6

| # | severity | finding | tags | file | disposition | Qodo now | cold caught |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Action required | A damaged block restores an old lead | 🐞 Bug, ≡ Correctness | room.py | fixed in 10c6583 | resolved | yes (cold M2 S3-1, S3-2, deferred as B-3, then fixed here) |
| 2 | Action required | Recovery can move the project checkout | 🐞 Bug, ☼ Reliability | room.py | fixed in 3e1d1ba | resolved | yes (cold M2 S1-4, deferred as B-2, then fixed here) |
| 3 | Action required | Block repair erases mission records | 🐞 Bug, ≡ Correctness | room.py | fixed in 10c6583 | resolved | yes (cold M2 S3-3) |
| 4 | Remediation recommended | Preflight can report no admin bypass when it couldn't read the ruleset | 🐞 Bug, ≡ Correctness | room.py | fixed in 3902adb | resolved | no |
| 5 | Remediation recommended | One lead can hide messages from another | 🐞 Bug, ≡ Correctness | room.py | fixed in 06c6164 | resolved | no |
| 6 | Remediation recommended | Recovery strands unpushed state commits | 🐞 Bug, ☼ Reliability | room.py | fixed in 3e1d1ba | resolved | yes (cold M2 S1-3) |
| 7 | Remediation recommended | A lead inside stale state cannot recover | 🐞 Bug, ☼ Reliability | room.py | fixed in 3e1d1ba | resolved | yes (cold M2 S1-5) |
| 8 | Remediation recommended | Weakened tests evade the merge hold | 🐞 Bug, ≡ Correctness | docs/design/m3-reviews-gate.md | deferred: B-4 to M3 (the finding is about the M3 spec draft, reviewed in M3's own PR; `BUILD-STATE.md`, "Deferred to later milestones") | open | no |
| 9 | Informational | A failed git diff makes state commit report 'nothing to commit' | 🐞 Bug, ☼ Reliability | room.py | fixed in a781937 | resolved | no |
| 10 | Informational | Preflight --fix failure prints no reason | 🐞 Bug, ◔ Observability | room.py | fixed in 04cd2f3 | resolved | no |

- Built from fetches 1 and 2 (`reviews/qodo/PR-6/`). Reviewed commit of fetch 2: `a7819374fe298f7392e483186191e470f51bce15`.
- Rounds: 1. Every round got a re-review.
- The three Action-required findings had been deferred from the cold reviews to M4; the severity rule doesn't let the lead defer them, so they were fixed here.
