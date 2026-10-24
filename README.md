# agent-room

A two-agent room on a GitHub issue. You talk to an **architect** (a Claude chat), and the architect directs a **builder** (a Claude Code cloud session) through the room.

There's no server and no allowlist to change, because both kinds of session already reach GitHub through `gh`. The issue thread doubles as the log, and you can read it or post into it from the GitHub app.

## How it works

- A room is one issue in this repo. A message is one comment, tagged with its sender's role.
- `room.py` posts and reads comments with `gh api`, and keeps a read cursor per role. If a machine is wiped, a participant resumes after its own last message.
- An agent "listens" by running `room.py wait` as a background command, which exits when the other side speaks. That exit is what wakes it.
- Only comments from the repo owner's account count, so nobody else can steer the builder.

The full protocol, including the loop and each role's rules, is in [`.claude/skills/agent-room/SKILL.md`](.claude/skills/agent-room/SKILL.md).

## Start a session pair

1. **Architect (chat):** "Start an agent room for <project> and act as architect." It attaches this repo, creates the room and tells you the number.
2. **Builder (Code tab, cloud session on the project repo, with this repo added too):** "Join agent room N as builder."
3. Talk to the architect from then on.

The chat needs the skill saved to your account. Cloud sessions load it automatically when this repo is in the session.

## Commands

```
room.py new "title"            room.py rooms
room.py say   N ROLE [TEXT|-]  room.py read N ROLE | --all
room.py wait  N ROLE           room.py close N ROLE [TEXT]
```

`wait` exits 0 for new messages, 3 on timeout (re-arm it), and 4 when the room is closed. Settings via environment: `ROOM_REPO`, `ROOM_TRUST`, `ROOM_STATE`.

## Tests

`python3 tests/test_room.py` runs everything against a fake `gh`, so no network is needed.

## Known limits

- **Latency:** polling every 5 seconds, plus the model's thinking time.
- **Idle pause:** a cloud VM may pause while it waits, which stops the waiter until you send that session a message. Not measured yet.
- **Usage:** every wake is a model turn on your plan.
