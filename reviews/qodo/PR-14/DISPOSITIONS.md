qodo: on
fetches: 1, 2, 3, 4, 5
reviewed: 0e3560a05240b8fad1731cc101d0b1460d76d143

# Qodo dispositions, PR #14

| # | severity | finding | tags | file | disposition | Qodo now | cold caught |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Action required | Lost start records trigger another lead | 🐞 Bug, ≡ Correctness | room.py | fixed in 5b5b852 | resolved | no |
| 2 | Remediation recommended | No automatic restart when a handover's successor dies | 🐞 Bug, ≡ Correctness | room.py | fixed in 1e22a22 | resolved | yes |
| 3 | Remediation recommended | Unrecorded rooms receive owner reminders | 🐞 Bug, ≡ Correctness | room.py | fixed in 1e22a22 | resolved | no |
| 4 | Remediation recommended | Other alarms delay owner reminders | 🐞 Bug, ≡ Correctness | room.py | fixed in 1e22a22 | resolved | no |
| 5 | Remediation recommended | A renewed state outage misses its alarm | 🐞 Bug, ≡ Correctness | room.py | fixed in 1e22a22 | resolved | no |
| 6 | Remediation recommended | Overlapping runs can start two leads | 🐞 Bug, ☼ Reliability | room.py | dismissed: watchdog runs don't overlap: it is one scheduled task, every 3 hours (hourly in drills), whose run takes about a minute. If two runs did overlap (Matthew running it by hand during a scheduled run), only one lead could work. Of two plain leads, the second's `lease take` exits 3; of two takeovers, the first loses the lease at its next lease check and stands down. The watchdog also never writes state, so it has nothing to claim atomically. Recorded under Known limits in docs/design/m6d-watchdog.md; cold M6d rounds 2 and 3 re-checked it (Fix checks, Q3) | resolved | no |

- Fetches: 1 (the first review, of bc901b7), 2 (of 12c63e4), 3 (of 7f808d4), 4 (of 2dc9386) and 5 (of 0e3560a).
- Reviewed commit of the last fetch: 0e3560a. All six findings are resolved there; Qodo resolved finding 6 at fetch 5, after the dismissal.
- Rounds with no re-review: none. The pushes of 7d9d6ce, 7d566f0, 8f19e11, 09ab31d and d5a5286 got no fetch of their own, but fetches 4 and 5 reviewed 2dc9386 and 0e3560a, which contain them.
- Finding 1's fix went through two steps. In 1e22a22 and 5328c17, a lead that joined after the stall began holds the start off. In 5b5b852, the watchdog tries only in the run that posts the stall's first alarm, which is posted before the fire, so a lost `LEAD-STARTED` can't lead to a second fire.
- Finding 2: a successor that never joined gets the start (1e22a22). One that joined and died is the architect's call since 5328c17, because it may be working (cold M6d R2-1). Qodo resolved the finding at fetch 2 and kept it resolved after that change.
- The cold column says whether a cold review raised the same problem on its own: finding 2 is cold M6d R1-5.
