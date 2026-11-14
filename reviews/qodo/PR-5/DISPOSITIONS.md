# Qodo dispositions, PR #5

| # | severity | finding (title as the tool prints it) | tags | file | disposition | Qodo now | cold caught |
|---|---|---|---|---|---|---|---|
| 1 | Action required | Approved design says builders push, build state says they never do | 🐞 Bug, ⚙ Maintainability | docs/design/v1.md | fixed in 6e1dbec | resolved | n/a |
| 2 | Remediation recommended | Watchdog loses its builder-progress signal | 🐞 Bug, ≡ Correctness | docs/design/v1.md | fixed in 6e1dbec | resolved | n/a |
| 3 | Remediation recommended | Review exemption by directory lets code skip coverage | 🐞 Bug, ⛨ Security | docs/design/v1.md | deferred: B-1 to M3 (`BUILD-STATE.md`, "Deferred to later milestones") | open | n/a |
| 4 | Remediation recommended | Preflight passes any 403 as no branch protection | 🐞 Bug, ⛨ Security | docs/design/BUILD-STATE.md | fixed in 8c9c413 | resolved | n/a |
| 5 | Informational | Platform-check checkboxes contradict recorded results | 🐞 Bug, ⚙ Maintainability | docs/design/v1.md | dismissed: the "To verify" list in `v1.md` lists the assumptions and is not a results record; the results live in `BUILD-STATE.md` ("Platform check"), which build-plan step 2 of `v1.md` now names (6e1dbec), per the 2026-11-14 decision in `BUILD-STATE.md` | open | n/a |

- Built from fetches 1, 2 and 3 (`reviews/qodo/PR-5/`). Reviewed commit of fetch 3: `8c9c413a98cbac3dc5dcfdc04a29ae1b470916f5`.
- Rounds: 2 (pushes of 3d78401 and 8c9c413). Every round got a re-review.
- `cold caught` is n/a: this docs-only PR had no cold review (`BUILD-STATE.md` decision of 2026-11-14).
