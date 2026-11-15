# Missions

```agent-room-state
lease_session: none
lease_generation: 0
phase: 1
room: 0
mission: none
step: none
pr: none
cursor: none
counter: 0
intent: none
waiting_for_owner: no
```

Owned by the lead. Only `room.py` edits the block above (`state set`, `state next`, `lease take`); edit the rest by hand and commit with `room.py state commit -m MSG`.

## Phase 1

| Mission | Branch | Status | PR | Criteria |
| --- | --- | --- | --- | --- |
| M1 | `mission/M1-<slug>` | planned | | P1-1 |

## Current mission

- **Spec revision:** <state-branch commit of PLAYBOOK.md and DESIGN.md>, pipeline <version>
- **Recorded step:** spec | build | cold round n | PR #n | Qodo round n | gate | waiting for owner
- **Ledger items:** none

### Tasks in flight

| Task | Branch | Attempt | Status |
| --- | --- | --- | --- |

### Parked questions

- none
