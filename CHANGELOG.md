# Changelog

Releases are immutable tags. Each entry gives the kind of release, what changed, and every migration step with its owner. Projects pin a version in `PLAYBOOK.md`; [`STABLE`](STABLE) names the one new projects pin.

## v1.0.0 (unreleased)

**Kind:** major. The pipeline of [`docs/design/v1.md`](docs/design/v1.md) replaces the single-skill agent room and its `docs/BUILD_PLAN.md` flow.

**Added**

- `room.py` v1: session-aware messages, the role guard, hyphenated kinds, buzzes by kind, links pinned to the release.
- The `agent-room/state` branch and the lead lease, with state writes that fail when someone else wrote first.
- `preflight`: checks the repo, its protection, the state branch and the environment, for architect and lead.
- Review records: cold reviews, Qodo archives, dispositions and the ledger.
- `gate` and `merge`: the merge gate, merge holds, and a merge bound to the reviewed head commit.
- Unattended operation: `handoff` and successor leads, `intent` and `reconcile`, the watchdog, budgets, `PAUSE` and `STOP`.
- Protocols: `ARCHITECT.md` and `LEAD.md`, and the thin skill.
- Briefs for the subagents, and manuals for Matthew with an "I want to…" index.

**Migration**

- Matthew: save the new skill in each Claude account, replacing the old one, and paste the Project instructions from `ARCHITECT.md` (section 2) into each project's Claude Project.
- Architect and lead: none. Rooms opened with the old skill don't carry over; start projects as `ARCHITECT.md` section 5 says.
