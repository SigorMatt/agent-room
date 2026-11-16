# agent-room

Build software with Claude while you're away from the keyboard. You design a project in a phone chat; a cloud session builds it as a series of reviewed, merged pull requests, and buzzes your phone only for decisions the design doesn't settle.

There's no server. The room is a GitHub issue in the project repo, the pipeline's state lives on the project's `agent-room/state` branch, and the machinery is this repo, released as immutable tags. The design is [`docs/design/v1.md`](docs/design/v1.md).

## Roles

| Role | What it is | Reads |
| --- | --- | --- |
| Matthew | The owner: designs, decides escalations and merge holds, does setup | [the manuals](docs/manual/README.md) |
| Architect | A chat in the project's Claude Project: designs with Matthew, writes `DESIGN.md` and `PLAYBOOK.md`, kicks off phases, posts decisions | [`ARCHITECT.md`](ARCHITECT.md) |
| Lead | A Claude Code cloud session, one per mission: plans, briefs subagents, triages reviews, merges, hands over to the next lead and starts it | [`LEAD.md`](LEAD.md) |
| Subagents | Builder, planner, cold reviewer, Qodo reader, auditor, survey | [`briefs/`](briefs/) |
| Lead task | One scheduled task per project with an API trigger, set up once by Matthew, that starts the leads: each run gets a join line as its text | [the manual page](docs/manual/set-up-the-lead-task.md) |
| Watchdog | A scheduled task every 3 hours that buzzes when no lead makes progress or none answers a decision, with a reminder every 12 hours; it starts no leads | — |

## Where to start

- **Matthew:** [`docs/manual/README.md`](docs/manual/README.md), the "I want to…" index: one-time setup, starting a project, answering a buzz, upgrading.
- **An architect chat:** [`ARCHITECT.md`](ARCHITECT.md). **A lead session:** [`LEAD.md`](LEAD.md).
- **Both** get there through the thin skill, [`.claude/skills/agent-room/SKILL.md`](.claude/skills/agent-room/SKILL.md), saved in each Claude account. It finds the project's pinned version and loads the protocol from that tag.
- **Versions:** [`STABLE`](STABLE) names the version new projects pin. [`CHANGELOG.md`](CHANGELOG.md) says what each release changed and how to upgrade.

## room.py

One Python file, standard library only, that reaches GitHub through `gh`. `python3 room.py --help` lists every command and exit code; `python3 room.py <command> --help` explains one. The main ones:

```bash
python3 room.py new "<title>" --repo OWNER/NAME      # open a room (architect)
python3 room.py say N lead "<message>"               # post; some kinds buzz the phone
python3 room.py read N architect                     # what's new for a role
python3 room.py wait N lead --timeout 540            # block until someone else posts
python3 room.py state sync                           # the state branch's worktree
python3 room.py lease take                           # one lead at a time
python3 room.py preflight --role lead --fix          # check the repo, state and environment
python3 room.py reconcile N                          # a joining lead: recorded state against GitHub
python3 room.py gate <PR>                            # the merge gate
python3 room.py merge <PR> --sha <sha>               # merge exactly the reviewed head
python3 room.py handoff N --step <step> --cursor <ID>   # hand over to the next lead
python3 room.py start-lead N lead                    # start the next lead through the lead task
python3 room.py join-line N                          # the line that starts a lead
```

## Safety

The pipeline acts as your GitHub account. Only your login's comments steer it. `main` changes only by merging a reviewed PR, and sensitive paths are held for you. On a public repo, the room and the state branch are readable by anyone.

## Tests

Standard library only, with `gh` and `curl` faked, so no network is needed:

```bash
for t in tests/test_*.py; do python3 "$t" || echo "FAILED $t"; done
```

`tests/test_docs.py` checks that every `python3 room.py` line in the protocols, briefs, manuals, this README and the skill parses, and that every relative link resolves.
