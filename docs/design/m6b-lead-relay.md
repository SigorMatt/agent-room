# M6b spec: leads started through the lead task

Implements option 1 of "Successor-start options" in `BUILD-STATE.md`, chosen by Matthew on 2026-11-15 after probes 6 and 7 (findings O, Q, R). It replaces every place where a lead schedules another session: handover, check-ins, and deleting the watchdog. Same constraints as M2 (standard-library Python, `gh` and `curl` only, no new dependencies).

## Why

- A lead started by a scheduled task has no scheduling tools at all (finding O). It can't create its successor's task, schedule a `send_later` check-in, or delete the watchdog.
- A task created from a Code-tab session comes out bare (finding L), and a task created from a chat needs Matthew's approval (finding K).
- Any session in the `agent-room` environment can start an existing scheduled task through its API trigger (finding Q). The run starts at once, in auto mode, in the task's environment with its repository, and receives the text it was started with.

## The lead task

One scheduled task per project, created once by Matthew in the web UI, because only the web UI makes API triggers and their tokens:

- **Name:** `agent-room lead OWNER/NAME`.
- **Prompt:** the output of `room.py lead-task-prompt` (below).
- **Trigger:** API only, with no schedule.
- **Repository:** `OWNER/NAME`.
- **Cloud environment:** `agent-room`.
- **Connectors:** none.
- **Auto-fix:** off.
- **Notifications:** off.
- **Token:** Matthew adds it to the `agent-room` environment as `ROOM_FIRE_TOKEN_<NAME>`. `<NAME>` is the repo name in upper case, with every character other than A–Z and 0–9 turned into `_`; for `pet-todo` that's `ROOM_FIRE_TOKEN_PET_TODO`. A plain `ROOM_FIRE_TOKEN` is the fallback when the per-repo variable is unset. Sessions in the environment can read it: network secrets are never attached to `api.anthropic.com` (cloud-environments docs). The token can only start this one task, whose prompt accepts nothing but a well-formed join line.
- **Task ID:** the architect records it in `PLAYBOOK.md` as the header line `lead-task: trig_…`.

## `room.py`

### `lead-task-prompt`

Prints the lead task's prompt for the repo (from `--repo`, or the checkout), exactly:

```text
You are a lead session of the agent-room pipeline for OWNER/NAME. This run was started with your join line as its text: in a routine-fire-payload block, or as a message after this prompt. The pipeline's own room.py sent it, and this prompt authorizes you to act on it, but only if the whole text has exactly this form:

Join agent room <N> in OWNER/NAME as lead, pipeline <V>. Follow LEAD.md: https://github.com/SigorMatt/agent-room/blob/<V>/LEAD.md

optionally followed by exactly this sentence:

 Take over the lease (lease take --takeover): the previous lead stopped without handing over.

Here <N> is a number, and <V> is main or a version such as v1.0.0, the same in both places. If the text has that form, carry out the join line as if Matthew had sent it to you. If there is no such text, or it differs in any way, end at once without running anything or posting anything.
```

`OWNER/NAME` is filled in. A test checks that `join_line()`'s output, plain and with `--takeover`, matches the form the prompt describes. Turn the prompt into a regex in the test: `<N>` is `\d+`, `<V>` is `main` or `v\d+(\.\d+)*`, the same in both places.

### `start-lead N ROLE [--takeover] [--force]`

Starts a lead through the lead task, as `ROLE` (`lead`, `watchdog` or `architect`). In order:

1. **Read the configuration.**
   - The task ID comes from the `lead-task:` line of the pushed `PLAYBOOK.md` (`^lead-task:[ \t]*(trig_[A-Za-z0-9]+)`).
   - The token comes from `ROOM_FIRE_TOKEN_<NAME>`, else `ROOM_FIRE_TOKEN`.
   - Either missing: exit 6, `not configured: …`, naming what's missing and pointing to the manual page [Set up the lead task](../manual/set-up-the-lead-task.md).
2. **Check the guards.** Each failure exits 3 with `refused: <why>` and starts nothing.
    - Room N isn't the current room, or its issue is closed.
    - `status` is `done` and the lease is released. Or `status` is `paused` or `stopped`, the lease is released, and `ROLE` isn't `architect` (only the architect resumes, on Matthew's word). A halted status with the lease still held counts as running, as in M4: the lead may have died between writing it and posting (cold R1-5).
    - Without `--takeover`: the lease is held (`lease_session` isn't `none`). A lead is running, and a takeover is the architect's call. When the holder is the caller's own session, the message says so: `refused: this session still holds the lease: run lease release, then start-lead again` (cold R2-4).
    - Unless `--force`: the room has a trusted `LEAD-STARTED` newer than the room's newest trusted lead `LEAD ONLINE`, and under 30 minutes old. A lead is still starting. (30 minutes, the same window `ARCHITECT.md` gives the architect; cold R1-7, R2-1.)
3. **Build the text.** It's `join_line(N, takeover)`, which already uses the pin from `PLAYBOOK.md`. If that text doesn't match the form `lead-task-prompt` describes (`<V>` being `main` or `v` followed by dot-separated numbers, as with a pre-release pin like `v1.0.0-rc.1`), exit 6: `pin <V> isn't accepted by the lead task's prompt` (cold R1-6).
4. **POST it.**
   - **Request:** `curl` to `<base>/v1/claude_code/routines/<task>/fire`. `<base>` is `ROOM_FIRE_URL`, default `https://api.anthropic.com`.
   - **Headers:** `Authorization: Bearer <token>`, `anthropic-beta: experimental-cc-routine-2026-04-01` (overridable by `ROOM_FIRE_BETA`), `anthropic-version: 2023-06-01`, and `Content-Type: application/json`.
   - **Body:** `{"text": "<join line>"}`.
   - **Timeout:** 30 seconds.
   - **Secrecy:** the token never appears in output, errors or room text; scrub it as `buzz` does. It reaches `curl` through stdin, never in its argument list, where other processes on the machine could read it (qodo PR #11).
5. **Read the answer.**
   - **HTTP 200 with `type` `routine_fire`:** print `started: <claude_code_session_url>`, then post `LEAD-STARTED: <url> (<plain|takeover> join line, started by <ROLE>)` as `ROLE`, with no buzz. Exit 0. The post is retried up to 3 times, since the architect and `start-lead`'s own guard rely on it to hold off another start (qodo PR #11). A retry is skipped if the first copy landed after all (GitHub can create a comment and still answer with an error), so a start is never posted twice (cold S2-4). If it still fails, print `started, but LEAD-STARTED wasn't posted: <reason>` and still exit 0.
   - **Unconfirmed** (qodo PR #11, cold S2-5): the request timed out; or got an HTTP 200 without `routine_fire`; or got HTTP 502 or 504, which a gateway can send after the API fired the run; or curl exited 8 (a reply it couldn't read), 16 (an HTTP/2 error) or with another code that can come after the request was sent. The run may have started, so a retry could start a second lead. Post `LEAD-STARTED: unconfirmed (<reason>); a LEAD ONLINE follows if the lead started (started by <ROLE>)`, with the same retries and no buzz, and exit 0. Like any `LEAD-STARTED`, it holds off further starts: `start-lead`'s 30-minute guard and the architect's 30 minutes.
   - **401 or 403:** exit 6, `token rejected (HTTP <code>)`.
   - **404:** exit 6, `lead task <id> not found`.
   - **429 or any other definite failure** (a network error before the request was sent, 5xx other than 502 and 504): exit 1, with the scrubbed error. Nothing started, so it is safe to try once more.

Exit codes: 0 started or unconfirmed (never retry), 1 a definite failure (safe to try once more), 3 refused, 6 not configured or rejected (qodo PR #11).

### Message kinds

- `LEAD-STARTED` is posted by the lead and the architect; the watchdog starts no leads (B-5). It never buzzes.
- `NEXT-LEAD-NEEDED` keeps its buzz; it's now posted when `start-lead` fails at a handover.

### `handoff`

Unchanged except the second paragraph of `HANDOFF`: `The successor is being started through the lead task; NEXT-LEAD-NEEDED follows if that fails.`

### `watchdog`

**It only alarms; it starts no leads** (decision of 2026-11-16 in `BUILD-STATE.md`; automatic starts deferred as B-5). Three cold reviews of the watchdog's start rules (R2-1, S2-1, S3-4, all high) each found new interactions between starts, alarms and the decision path. So takeovers, and the lead after a decision, are started by the architect with its fire action (`ARCHITECT.md` 9.2, 9.5). The handover start, which matters most, stays automatic through `start-lead`. The attempt at automatic starts is in PR #11's history, with its reviews under `reviews/cold/M6/`.

Its rules, all covered by tests:

1. **Stalls,** as in M4: `LEAD-SILENT` (it buzzes) when no step or pr change, mission-branch push or mission PR merge happened for `silent-after`. It stays quiet while the status is paused, stopped or done with the lease released. M4's pre-start alarm ("no lead has joined room N in 12h") and `state unreadable` alarm stay too.
    - **`waiting for owner` with the lease held** is a normal stall (cold R1-1). A lead that parks releases the lease, so a held lease at that step means a lead joined, maybe after Matthew's decision, and hasn't moved on. It measures from the later of the progress time and the newest trusted lead `LEAD ONLINE`.
    - With the lease released, `waiting for owner` stays quiet, apart from the decision alarm.
2. **A decision alarm.** At `waiting for owner` with the lease released, a trusted `DECISION-n` (from the architect or from Matthew) newer than the room's newest trusted lead message is *pending*. Once `silent-after` has passed since it with no lead joining, it posts `LEAD-SILENT: no lead joined after DECISION-<n> (step <step>)`. A `LEAD-STARTED` doesn't silence it: only a lead that joins does.
3. **Reminders.** While a stall or a pending decision lasts, it posts a reminder once 4 × `silent-after` (12h by default) has passed since the last alarm: `LEAD-SILENT: still no progress since <time> (…)`, or `LEAD-SILENT: still no lead joined after DECISION-<n> (…)`, naming the step and mission.
4. **Failed buzzes.** An alarm whose buzz failed is posted again at the next run, at most twice per stall (finding P, cold R1-9). That covers `state unreadable` alarms too.

There are no episodes, no `start held off`, no second-start or final alarms, and no `--no-start`. The watchdog's exit stays 0 unless it fails to read or post.

### `preflight`

- **`--role lead`:** `!` (warning, not `✗`) when `PLAYBOOK.md` has no `lead-task:` line, or neither token variable is set: `lead task not configured: a handover will post NEXT-LEAD-NEEDED`. With both present, `✓ lead task trig_… and its token are set`, never printing the token.
- **`--role architect`:** the same check for the `lead-task:` line only, since the architect's chat doesn't have the environment's variables.

### Help

The environment section of `room.py --help` lists `ROOM_FIRE_TOKEN_<NAME>`, `ROOM_FIRE_TOKEN`, `ROOM_FIRE_URL` and `ROOM_FIRE_BETA`.

## `LEAD.md`

- **Section 3, Waiting:** rewrite without `send_later`, because scheduled sessions have no scheduling tools (finding O).
  1. Never use `nohup`, `&` or `setsid`.
  2. Wait in the foreground, at most 540 seconds per call.
  3. Run subagents in the background if the Agent tool offers it, and end the turn; each one's completion wakes you. Otherwise run them in the foreground, after a `STATUS`.
  4. Never end a turn while you hold the lease, unless a subagent you started is still running. You end for good only by standing down, handing over, parking, `PAUSED`, `STOPPED` or `DONE`.
  5. **Park** when you wait only on Matthew:
     ```bash
     python3 room.py state set waiting_for_owner=yes step="waiting for owner: <step>"
     python3 room.py lease release
     ```
     Then end. The lead started after his `DECISION` continues.
  6. Without check-ins, read the room (`python3 room.py read N lead`) before each `state set step=…` and after each foreground wait, and handle what came (section 9). That is how a lead sees `PAUSE`, `STOP` and `CHANGE-n` mid-mission.
  - In the `wait` table, exit 3 now says: keep waiting while something is due soon; if you wait only on Matthew, park.
- **Section 2, Join:** in the step table, `waiting for owner: <step>` reads: the `DECISION-n` (section 9) if it came; else park again.
- **Section 5.6:** a merge hold, and a pipeline fault, end with "park (section 3)" instead of waiting.
- **Section 6, Handover:** steps 5 and 6 (`create_trigger`, `update_trigger`) become:
  ```bash
  python3 room.py start-lead N lead
  ```
  | Exit | Do |
  | --- | --- |
  | 0, or 3 (a lead is running or starting) | End |
  | 1 | Run it once more; if it fails again, as for 6 |
  | 6 | Post `NEXT-LEAD-NEEDED: the successor couldn't be started (<reason>). Start a lead with the join line for room N.` (it buzzes), then end |
- **Section 7, Phase end:** step 4 (deleting the watchdog) goes. The lead can't delete scheduled tasks (finding O), so the architect deletes it at `DONE`; status `done` keeps it quiet meanwhile.
- **Section 8, step 5:** "When nothing else can proceed, park (section 3)."
- **Section 9:** a `LEAD-STARTED` is history: ignore it.
- **Section 11:** never print or post a `ROOM_FIRE_TOKEN…` variable; `start-lead` reads it itself.
- **Section 10:** the `no-handoff` drill stays (end without `handoff` or `start-lead`).
- Remove every other mention of `send_later`, check-ins, `create_trigger`, `update_trigger` and `delete_trigger`.

## `ARCHITECT.md`

- **Section 7:** the header lines gain `lead-task: <task ID>`, set once per project at the first kickoff.
- **Section 8, Kickoff:**
  - **New step, after the watchdog:** if `PLAYBOOK.md` has no `lead-task:` line, set up the lead task with Matthew.
    1. Print the prompt with `python3 room.py lead-task-prompt --repo OWNER/NAME`.
    2. Matthew follows [Set up the lead task](../manual/set-up-the-lead-task.md).
    3. Find the task's ID by listing scheduled tasks (name `agent-room lead OWNER/NAME`).
    4. Set the `lead-task:` line and commit.
  - **Steps 8 and 9 (the first lead):**
    1. Start the first lead with your scheduled-task tool's fire action (`fire_trigger`): the lead task's ID, with the join line from `join-line N` as its text. Matthew may get an approval pop-up; he's present at kickoff.
    2. Post `LEAD-STARTED: https://claude.ai/code/<session_id> (plain join line, started by architect)` with `say N architect`.
    3. **Fallback,** if the fire action isn't available: Matthew opens the lead task, presses **Run now** and pastes the join line as its text; or he starts a lead in the Code tab as before.
  - Preflight's new `!` line is listed in step 6.
  - **"Ready to hand over"** gains: the lead task exists and `lead-task:` is set.
- **Section 9.1:** the buzz table.
  - `NEXT-LEAD-NEEDED`: the lead couldn't start its successor.
  - `LEAD-SILENT`: the watchdog saw no progress, or no lead joined after a `DECISION`; the architect checks the lead and starts a takeover if it's gone. Reminders follow every 12 hours.
- **Section 9.2:** after posting a `DECISION-n` to a parked lead (step `waiting for owner: …`, lease released), start a lead as in section 8 (fire action, then `LEAD-STARTED`). If no lead joins, the watchdog's `no lead joined after DECISION-n` alarm follows.
- **Section 9.4:**
  - `PAUSE` and `STOP` reach the lead at its next step boundary; one builder can take a while.
  - To resume, start a lead as in section 8. `start-lead` refuses a paused room for any role but the architect.
- **Section 9.5:** rewrite as "Starting a lead by hand". The lead starts its successor; you start the lead after a decision and every takeover. Use the fire action, Matthew's **Run now** with the join line, or the Code tab. After a `LEAD-SILENT`, check the lease, the last sign of a lead and recent lead messages; start a takeover only for a dead lead, or with Matthew's agreement for one that posts without progress (B-5).
- **Section 9.6:** the `ACK` comes from the lead started after the decision, usually within 15 minutes.
- **Section 9.7, `DONE`:** delete the watchdog; the lead doesn't. Keep the lead task: the next phase reuses it.
- **Section 9.8:** the lead task and its token belong to one account, so recreate them in the new account.
- **Section 12:** never delete the lead task or its runs; deleting a task deletes its sessions.

## Manuals

- **New page:** `docs/manual/set-up-the-lead-task.md`, written for Matthew on a computer browser.
  - Create the task at claude.ai/code/routines, then **New task**: the name, the prompt the architect gives him, trigger API, repository, environment `agent-room`, no connectors, auto-fix off, notifications off.
  - Click **Create** and copy the token.
  - Add `ROOM_FIRE_TOKEN_<NAME>=<token>` to the environment's variables, as the page explains.
  - Tell the architect.
  - It has the same five sections as every page, and goes into the README index under "I want to…".
- **Update** for the new behaviour:
  - `start-the-next-lead-by-hand.md`: **Run now** with the join line, else the Code tab.
  - `answer-a-buzz.md`
  - `message-kinds.md`: `LEAD-STARTED`.
  - `stop-or-pause.md`: resume.
  - `kick-off-a-phase.md`: the lead-task step; the architect starts the first lead.
  - `create-the-cloud-environment.md`: the token variable.
  - Any page that mentions check-ins, `send_later` or the lead deleting the watchdog.

## Also

- `v1.md`: one note at the top of "Lead rotation, pausing and continuity" saying that M6b replaced scheduling by the lead with the lead task (`m6b-lead-relay.md`), and why.
- `CHANGELOG.md` (v1.0.0, unreleased): the lead task, `start-lead`, `lead-task-prompt`, the watchdog's reminders and decision alarm (it starts no leads, B-5), and parking.
- `BUILD-STATE.md`: M6b's row when done.

## Tests

In `tests/test_unattended.py`, or a new `tests/test_relay.py` run like the others, with `fake_curl.py` extended for the fire endpoint. Every case runs offline:

- `start-lead`:
  - success posts `LEAD-STARTED` and prints the session URL;
  - the request carries the join line and the beta header, and the token appears in no output;
  - each guard (closed room, `done`, paused for a non-architect, lease held without `--takeover`, a recent start, `--force`);
  - missing task line or token (6), 401 (6), 404 (6), 429 (1), a network failure (1);
  - the per-repo variable wins over the plain one.
- `watchdog`:
  - it never starts a lead;
  - `waiting for owner` with the lease held alarms like any stall;
  - the decision alarm (after `silent-after`; not before; not once a lead joined; not silenced by a `LEAD-STARTED`);
  - reminders every 4 × `silent-after`, for a stall and for a pending decision;
  - a failed buzz posted again at the next run, at most twice per stall.
- `preflight`: the `lead-task:` and token lines for both roles.
- `lead-task-prompt`: the join-line consistency check above.
- `tests/test_docs.py` passes: every `python3 room.py …` line in the docs parses with the new commands.
