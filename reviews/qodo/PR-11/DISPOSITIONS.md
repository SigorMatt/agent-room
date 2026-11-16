qodo: on
fetches: 1, 2, 3, 4, 5
reviewed: 073f19de6e3ebc5d3138a385ca7651dbb7994827

# Qodo dispositions, PR #11

| # | severity | finding | tags | file | disposition | Qodo now | cold caught |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Action required | Unrecorded starts can spawn another lead | 🐞 Bug, ☼ Reliability | room.py | fixed in f978b05 | resolved | no |
| 2 | Action required | A retry can start two leads | 🐞 Bug, ☼ Reliability | room.py | fixed in 0a9661a | resolved | no |
| 3 | Remediation recommended | Buzz instructions can start a second lead | 🐞 Bug, ≡ Correctness | docs/manual/answer-a-buzz.md | fixed in 661e553 | resolved | no |
| 4 | Remediation recommended | Watchdog can take over from a working lead | 🐞 Bug, ☼ Reliability | room.py | fixed in 760e421 | resolved | no |
| 5 | Remediation recommended | A failed post-decision lead leaves the room silent forever | 🐞 Bug, ☼ Reliability | room.py | fixed in bc41190 | resolved | no |
| 6 | Remediation recommended | Other processes can read the fire token | 🐞 Bug, ⛨ Security | room.py | fixed in 8ec36b0 | resolved | no |
