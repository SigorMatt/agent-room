# M2 spec: `room.py` v1 command surface

The interface that the M2 builders implement and the M3 protocol docs (`ARCHITECT.md`, `LEAD.md`) call. It implements `v1.md`; where the two differ, `v1.md` plus `BUILD-STATE.md` decisions win, and this file gets fixed.

`room.py` stays one file, standard library only, Python 3.9+, run as `python3 room.py …`. GitHub access only through the `gh` CLI (`gh api`) and `git`. Existing behaviour keeps working unless this spec changes it.

## Constants and identity

- `VERSION = "main"` at the top of the file. A release sets it to the tag (`v1.0.0`). Every link `room.py` writes uses `https://github.com/SigorMatt/agent-room/blob/{VERSION}/…`.
- **Session ID:** `--session`, else env `ROOM_SESSION`, else the first 8 characters of env `CLAUDE_CODE_SESSION_ID`, else the hostname.
- **Repo:** `--repo OWNER/NAME`, else `$ROOM_REPO`, else the checkout's GitHub remote (existing behaviour).

## Messages

- **Format:** `<!-- agent-room role=ROLE session=SID -->\n**[ROLE · SID]**\n\nTEXT`. Parsing still accepts the old format without `session=`.
- **Own messages** are those with the same role **and** session. `read`/`wait` hide only those, so a lead sees other leads' messages (needed for `LEAD ONLINE`).
- **Kinds:** the leading token of the text, after stripping leading whitespace and markdown decoration (`*`, `_`, `` ` ``, `>`, `#`). Multi-word kinds are matched from a fixed list first: `LEAD ONLINE`, `ACK DECISION-n`, `ACK CHANGE-n`. Otherwise the kind is the leading run of `[A-Z]` words joined by `-`, with a trailing `-<digits>` kept (`MERGE-HOLD-4`, `NEXT-LEAD-NEEDED`, `ESCALATION-3`).
- **Role guard** (exit 2, nothing posted):
    - role `lead` cannot send `DECISION`, `CHANGE`, `PAUSE`, `STOP`;
    - role `architect` cannot send `PLAN`, `LEAD ONLINE`, `STATUS`, `ESCALATION`, `MERGE-HOLD`, `HANDOFF`, `NEXT-LEAD-NEEDED`, `PAUSED`, `STOPPED`, `DONE`, `ACK …`;
    - role `watchdog` can send only `LEAD-SILENT`;
    - role `human` stays rejected;
    - any other role is rejected: only `lead`, `architect` and `watchdog` post.
- **Automatic buzz:** `say` buzzes when the kind is one of `ESCALATION`, `MERGE-HOLD`, `NEXT-LEAD-NEEDED`, `PAUSED`, `STOPPED`, `DONE`, `LEAD-SILENT`. `--buzz` forces one, `--no-buzz` suppresses one. Buzz title: `<KIND> · <repo name> room <N>`; body: `<KIND> from <role> in <OWNER/NAME> room <N>`; click: the comment URL. Never the text.
- **Lease check on send:** when role is `lead` and a state worktree exists (see State), `say` and `close` refuse with exit 5 if another session holds the lease. A released lease (`none`) doesn't block posting, so a retiring lead can still post `NEXT-LEAD-NEEDED`. No kind is exempt: `LEAD ONLINE` is posted after taking the lease.

## Room commands

| Command | Behaviour |
| --- | --- |
| `new TITLE` | Creates the label if missing, opens the issue with the label, body links `ARCHITECT.md`/`LEAD.md` at `VERSION`. Prints `room N in OWNER/NAME: URL` |
| `rooms` | Open labelled issues (existing) |
| `say N ROLE [TEXT\|-] [--buzz\|--no-buzz]` | Post; prints `sent #<comment id>`, plus `[buzz sent]` or `[buzz failed: …]` |
| `read N ROLE` | Unseen messages since the cursor (existing), hiding own messages |
| `read N ROLE --from ID` | Sets the cursor to comment ID first, then reads everything after it. Used by a joining lead |
| `read N --all` | Whole transcript (existing) |
| `wait N ROLE` | Existing exit codes (0 new, 3 timeout, 4 closed, 1 errors). Prints `[cursor: <last id>]` as its last line on exit 0 |
| `close N ROLE [TEXT] [--buzz\|--no-buzz]` | Existing (closes first, then posts); buzzes like `say` |
| `cursor N ROLE` | Prints the stored cursor's comment ID, or `none` |
| `ping` | Existing |

## State branch

The playbook and pipeline state live on branch `agent-room/state` of the project repo, under `docs/playbook/`. `room.py` keeps a git worktree of that branch at `$ROOM_STATE_DIR`, default `~/agent-room-state/<OWNER>__<NAME>`, created from the project checkout (`git worktree add`) or, without one, a shallow clone of the branch.

| Command | Behaviour |
| --- | --- |
| `state init` | Architect, at kickoff. If `main` has no commits, creates and pushes a first commit on `main` (`README.md` with the repo name, `.gitignore`). If `agent-room/state` doesn't exist, creates it as an orphan branch with the architect templates (`PLAYBOOK.md`, `DESIGN.md`, `HANDOFF.md`) and pushes it. Idempotent |
| `state init-lead` | Lead. Adds missing lead-owned files from templates (`MISSIONS.md`, `LEDGER.md`, `QODO-VALUE.md`) and pushes. Idempotent |
| `state path` | Prints the worktree path, creating or syncing it first |
| `state sync` | Fetches and hard-resets the worktree to `origin/agent-room/state` |
| `state commit -m MSG` | Commits all changes in the worktree and pushes. Changes to lead-owned files require the lease (exit 5). If the push is rejected because the branch moved (the remote is neither the commit the work was built on nor this commit; a remote that already holds this commit is a success): exit 3, prints `state moved: run 'state sync', re-read, re-apply`, leaves the worktree reset to the remote |
| `state get KEY` | Prints a value from the machine block of `MISSIONS.md` |
| `state set KEY=VALUE …` | Sync, set, commit and push in one step (exit 3 on a lost race). Requires that this session holds the lease (exit 5), except `lease take`'s own write |
| `state next counter` | Increments `counter`, pushes, prints the new value (for `ESCALATION-n` / `MERGE-HOLD-n`). Requires the lease (exit 5) |
| `lease take [--takeover]` | Sync. If `lease_session` is another session, exit 3 (`lease held by X: stand down`), unless `--takeover`. Otherwise `lease_generation += 1`; `lease_session = <session>`; commit and push. Prints the generation. Exit 3 if another session pushed first |
| `lease release` | The holder sets `lease_session: none` and pushes. Leads release at `HANDOFF`, `PAUSED`, `STOPPED` and `DONE`, so the next lead's plain `lease take` wins and a duplicate launch stands down. `--takeover` is only for a lead Matthew starts after `LEAD-SILENT` |
| `lease check` | Fetch; exit 0 if `lease_session` is this session, else exit 5 and print the holder |

**Machine block.** The top of `MISSIONS.md` holds one fenced block that only `room.py` edits:

````markdown
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
````

Values are single-line strings. Unknown keys are kept.

## Preflight

`preflight --role architect|lead [--fix]` prints one line per check (`✓`, `✗` or `!` for a warning) and exits 0 only if no `✗`.

| Check | Roles | Fail or warn |
| --- | --- | --- |
| Push access (`permissions.push`) | both | ✗ |
| `main` has commits | both | ✗ (architect: suggests `state init`) |
| `main` requires approving reviews, in classic protection or in rules for the branch. A 404 means none; a 403 that mentions upgrading means none (private repo on GitHub Free) | both | ✗, naming where the rule is |
| Admin bypass: `enforce_admins` off, or ruleset bypass actors | both | ! report only |
| `delete_branch_on_merge` | both | ! asks Matthew to turn on "Automatically delete head branches" |
| `agent-room/state` exists with `PLAYBOOK.md` and `DESIGN.md`, and `PLAYBOOK.md` has a `pipeline: v…` line, read from the pushed branch, not the worktree | both | ✗; `pipeline: main` is `!` (development builds before `v1.0.0`) |
| Lead-owned files exist | lead | ✗ (`--fix` runs `state init-lead`) |
| `ROOM_NTFY_TOPIC` set; `QODO_REVIEW` is `on` or `off` | lead | ✗ |

Tests on `main` are run by the lead itself using the playbook's `test:` line; preflight does not run them.

## Tests

Extend `tests/test_room.py`, still with fake `gh` and `curl`. Add a fake or local bare git remote for state commands (a bare repo in a temp dir as `origin`). Cover at least: session-aware hiding, `--from`, kinds incl. hyphenated and multi-word, every role-guard rule, auto-buzz kinds, lease take/check including a lost race between two sessions, `state commit` rejection, `state next counter`, `state init` on an empty repo, and each preflight check's pass and fail.

## Changes after cold review round 1

The lease rows, the lease check on send, `close` buzzing, markdown-wrapped kinds, unknown roles and the preflight pin row above were changed by the M2 cold review (`reviews/cold/M2/round-1.md`, findings R1-1 to R1-15).
