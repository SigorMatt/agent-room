# agent-room

Build with Claude while you're away from the keyboard, and get pulled in only when a real decision comes up.

- **Architect:** a Claude chat on your phone. You design with it, and it writes the design and the build plan into the repo.
- **Lead:** a Claude Code cloud session that builds the plan. It hands tasks to builder subagents, answers their questions from the design, and escalates only what the design doesn't settle.
- **Escalation:** the lead posts in a GitHub issue of the project and **buzzes your phone** through [ntfy](https://ntfy.sh). You open the architect chat, decide together, and the architect updates the docs and posts the decision. The lead picks it up and carries on.

There's no server to run: the room is a GitHub issue, and both sessions already reach GitHub as you.

---

## Walkthrough: from zero to a working build

You'll build a tiny Python todo CLI in a fresh repo, deliberately leaving one question open so you can watch an escalation happen. Setup takes about 15 minutes, and the build about 20. Each step says what you should see.

### 0. One-time setup

**a. Make this repo public.** On GitHub, open `agent-room` → **Settings** → **Danger Zone** → **Change visibility** → **Public**. Sessions can then download `room.py` without being given access to this repo.

**b. Add the skill to your Claude account.** Save it from the proposal card in the chat where this was built, or upload `.claude/skills/agent-room` in Claude's skill settings. Your chats and cloud sessions pick it up from there.

**c. Connect GitHub to Claude** on each account you'll use. The Code tab asks for this on first use.

**d. Install ntfy and pick a topic.**
1. Install **ntfy** on your phone (Google Play or F-Droid).
2. Make up a long, unguessable topic name, for example `agentroom-` followed by 16 random letters and digits. On ntfy.sh, anyone who knows the name can read the topic. The buzz only ever says something like "ESCALATION-1 in pet-todo room 1", but keep the name to yourself anyway.
3. In the ntfy app, tap **+**, enter the topic and keep the server as `ntfy.sh`. You don't need an account (see [About ntfy limits](#about-ntfy-limits)).

**e. Create a cloud environment for the lead.** This is easiest in a browser at [claude.ai/code](https://claude.ai/code): open the environment selector under the message box, then **New environment**.
- **Name:** `agent-room`
- **Network access:** **Custom**. Put `ntfy.sh` in **Allowed domains** and tick **Also include default list of common package managers**.
- **Environment variables:** `ROOM_NTFY_TOPIC=<your topic>`

**f. Test the buzz.** Start a cloud session in the `agent-room` environment on any repo and send:

> Run: `curl -fsSL https://raw.githubusercontent.com/SigorMatt/agent-room/main/room.py -o ~/room.py && python3 ~/room.py ping`

**Check:** your phone buzzes with "agent-room test". If it doesn't, see [Troubleshooting](#troubleshooting). Archive this session afterwards.

### 1. Create the pet project

In the GitHub app, create `pet-todo` and tick **Add a README**.
- **Private:** only you can read the room.
- **Public:** anyone can read the room, but only your account can steer it.

### 2. Design with the architect (chat)

Open a **new chat** in the Claude app and send:

> Start an agent room in SigorMatt/pet-todo and act as architect. Let's design a tiny Python command-line todo app: add, list and done, stored in a JSON file, with pytest tests. Also plan a "due date" feature, but leave the date format undecided in the design. I want to test an escalation.

What you should see:
- If Claude asks to connect `pet-todo`, approve it.
- It discusses the design with you. Answer its questions.
- It commits `docs/DESIGN.md` and `docs/BUILD_PLAN.md`, creates the room, and gives you a line for the lead, such as `Join agent room 1 in SigorMatt/pet-todo as lead. Build from docs/BUILD_PLAN.md.`

**Check:** both docs are in the repo, and issue #1 has the purple `agent-room` label.

### 3. Start the lead (cloud session)

In the Claude app, open the **Code** tab and start a new session:
- **Repository:** `pet-todo`
- **Environment:** `agent-room`

Send the line the architect gave you.

What you should see:
- The lead reads the docs, starts a background waiter, and hands the first tasks to builder subagents.
- `STATUS: T-1 done …` lines appear in the issue as tasks finish.

**Check:** a running background command in the session, and STATUS comments in the issue. You can now put the phone away.

### 4. The escalation

When a builder reaches the due-date task, the date format is undecided and changes user-visible behavior, so the lead escalates. Meanwhile it carries on with other tasks.

What you should see:
1. Your phone buzzes: **ESCALATION-1 · pet-todo room 1**. Tapping it opens the issue, which shows the question, the options and the lead's recommendation.
2. Open the architect chat and say *"check the room"*. It summarizes the question, and you decide together, for example "ISO dates, YYYY-MM-DD".
3. The architect records the decision in `DESIGN.md`, commits it, and posts `DECISION-1: …`.
4. Within seconds, the lead posts `ACK DECISION-1` and resumes the blocked task.
   - If no ACK comes within about 2 minutes, the architect will tell you. Open the lead's session in the Code tab and send *"check the room"*.

### 5. Done

When every task is ticked, the lead opens a PR and buzzes you: **DONE · pet-todo room 1**. Review and merge it. Then tell the architect *"wrap up"*: it closes the room, and the lead's waiter stops.

### 6. Test a long idle stretch (once)

Step 4 shows that the lead's waiter survives short waits. To check longer ones, wait **at least an hour** after the next escalation buzz before you post the decision.
- **The ACK arrives on its own:** waiters survive long idle stretches, and you never need to nudge.
- **It doesn't:** the session's machine paused. Nudge it, and expect to nudge after long gaps.

---

## About ntfy limits

ntfy.sh counts usage per IP address, unless you're on a **paid** tier. That covers anonymous senders and free accounts alike: a free account token changes nothing. The limit is 250 messages a day per address, and cloud sessions share outgoing addresses with other users. Escalations are a few a day, so you'll most likely never hit it, and when you do, the escalation is still posted. Only the buzz is lost, and the lead mentions it in its next STATUS.

If `[buzz failed: … 429 …]` keeps showing up, move to your own per-account limit:
1. Subscribe to a paid ntfy.sh tier (Supporter is about $6 a month at the time of writing). Then in the ntfy web app, open **Account** → **Access tokens** and create a token. It starts with `tk_`.
2. Give the token to the `agent-room` environment in one of two ways:
   - **Network secret (best):** the session never sees the token. Under **Network secrets**, add a secret with **Allowed websites** `ntfy.sh` and a custom header named `Authorization`, prefix `Bearer`, with the token as the value.
   - **Environment variable:** `ROOM_NTFY_TOKEN=tk_…`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ping` says `ROOM_NTFY_TOPIC is not set` | The session isn't using the `agent-room` environment, or the variable is missing from it. |
| `[buzz failed: … 403 …]` | `ntfy.sh` isn't in the environment's allowed domains. |
| `[buzz failed: … 429 …]` | The shared-IP limit. See [About ntfy limits](#about-ntfy-limits). |
| The buzz was sent but the phone stayed quiet | The topic in the app doesn't match the environment variable exactly, or Android is restricting ntfy's battery use. |
| No ACK after a DECISION | The lead's waiter isn't running. Send *"check the room"* in its Code session. |
| `GitHub access to this repository is not enabled for this session` | The session lacks push access. Architect: approve the repo connection. Lead: start the session on that repo. |
| Downloading `room.py` fails (404) | `agent-room` is still private (step 0a). |
| `[ignored N message(s) from untrusted authors: X]` | The sessions post as different GitHub logins. Tell both to use `ROOM_TRUST=SigorMatt,X`. |
| Every comment ends with "Generated by Claude Code" | Claude's GitHub proxy adds it. The client strips it when reading. |

## How it works

- A room is an issue labelled `agent-room` in the project repo, and a message is one comment, tagged with its sender's role.
- `room.py` reads and posts with `gh api`, and keeps a read cursor per role. If a machine is wiped, a participant resumes after its own last message.
- The lead listens by running `room.py wait` as a background command, which exits when someone posts. The architect doesn't listen at all: you bring it in.
- `say --buzz` posts the message, then pushes a notification carrying only the message kind and room. A failed push never fails the post.
- Only comments from your own GitHub login count, so nobody else can steer the build.
- The full protocol is in [`.claude/skills/agent-room/SKILL.md`](.claude/skills/agent-room/SKILL.md).

## Commands

```
room.py new "title"                  room.py rooms
room.py say   N ROLE [TEXT|-] [--buzz]
room.py read  N ROLE | --all         room.py wait N ROLE
room.py close N ROLE [TEXT]          room.py ping
```

- **Which repo:** room commands take `--repo OWNER/NAME`. Without it, the client uses `$ROOM_REPO`, then the checkout's GitHub remote.
- **`wait` exit codes:** 0 for new messages, 3 on timeout (re-arm it), 4 when the room is closed.
- **Environment:** `ROOM_NTFY_TOPIC`, `ROOM_NTFY_SERVER`, `ROOM_NTFY_TOKEN`, `ROOM_TRUST` and `ROOM_STATE`.

## Tests

`python3 tests/test_room.py` runs everything against a fake `gh` and a fake `curl`, so no network is needed.

## Known limits

- **Latency:** polling every 5 seconds, plus the model's thinking time.
- **Usage:** every builder subagent and every wake is model usage on your plan. Parallel builders spend it faster.
- **Long idle stretches:** step 6 measures whether a paused machine stops the lead's waiter.
