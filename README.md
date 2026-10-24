# agent-room

Two Claude sessions working on one project through a GitHub issue. You talk to an **architect** (a Claude chat on your phone). The architect directs a **builder** (a Claude Code cloud session) by posting in an issue of the project's repo.

There's no server, nothing to host and no network setting to change: both kinds of session already reach GitHub as you. The issue doubles as the log, and you can read it or post into it from the GitHub app.

---

## Walkthrough: from zero to a working pair

You'll build a tiny Python todo CLI in a fresh repo. It takes about 20 minutes, and each step says what you should see.

### 0. One-time setup

1. **Make this repo public.** On GitHub, open `agent-room` → **Settings** → **Danger Zone** → **Change visibility** → **Public**. Sessions can then download `room.py` without being given access to this repo. Nothing secret lives here.
2. **Add the skill to your Claude account.** Save it from the proposal card in the chat where this was built, or upload `.claude/skills/agent-room` in Claude's skill settings. Chats and cloud sessions on that account then pick it up. If the builder runs on another account, add it there too.
3. **Connect GitHub to Claude** on each account you'll use. The Code tab asks for this on first use.

Network settings don't need any change. Chat's "Package managers only" and the cloud **Default** environment both already allow GitHub.

### 1. Create the pet project

In the GitHub app, create a repo named `pet-todo` and tick **Add a README**.
- **Private:** only you can read the room.
- **Public:** anyone can read the room, but still only your account can steer it.

**Check:** the repo exists with one commit.

### 2. Start the architect (chat)

Open a **new chat** in the Claude app and send:

> Start an agent room in SigorMatt/pet-todo and act as architect. The project: a tiny Python command-line todo app with `add`, `list` and `done`, stored in a JSON file, with pytest tests.

What you should see:
- If Claude asks to connect `pet-todo`, approve it. The architect needs it to create the room and to review the builder's work.
- It replies with the room number and a line to paste into the builder, such as `Join agent room 1 in SigorMatt/pet-todo as builder.`
- It may ask a couple of questions about the app before sending any work. Answer them.

**Check:** `pet-todo` has issue #1 with the purple `agent-room` label.

### 3. Start the builder (cloud session)

In the Claude app, open the **Code** tab and start a new session:
- **Repository:** `pet-todo`
- **Environment:** Default

Send the line the architect gave you:

> Join agent room 1 in SigorMatt/pet-todo as builder.

What you should see:
- It downloads `room.py`, reads the room and starts a background waiter.
- If the architect already posted a task, the builder picks it up straight away. Otherwise it stays quiet.

**Check:** the session shows a running background command. From here on, you don't type in this session.

### 4. Collaborate

Go back to the architect chat and say: *"Go ahead with the first task."*

In the issue you'll see:
1. **[architect]** `TASK-1: …`, with Goal, Context, Constraints and Done when.
2. **[builder]** `ACK TASK-1` and a one-line plan, within seconds.
3. **[builder]** `DONE TASK-1`, a few minutes later, with the branch or PR, the tests run and any decisions.
4. The architect reviews it, tells you what happened in one to three lines, and either sends TASK-2 or asks you something.

**Check:** a branch or PR with working code and passing tests, which you never asked the builder for directly.

### 5. Steer from GitHub (optional)

Comment on the issue from the GitHub app, for example: *"Use argparse only, no third-party packages."* Both agents receive it as `human (SigorMatt)`, and it outranks the architect.

### 6. Test the idle pause

This is the one open question, and this step answers it. Leave both sides quiet for at least 15 minutes, then comment on the issue from GitHub: *"Ping: both of you reply 'here'."*
- **Both reply within about 10 seconds:** waiters survive an idle VM, and nothing more is needed.
- **One stays silent:** its VM paused and the waiter died. Open that session, send *"check the room and re-arm your waiter"*, and note which side it was. That decides whether this project needs an outside waker.

### 7. Finish

Tell the architect *"wrap up"*. It posts a summary and closes the issue, and the builder's waiter exits and stops. Merge the PR yourself.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Builder went silent after a task | Its waiter isn't running, or its VM paused. In the Code tab, send *"check the room and re-arm your waiter."* |
| `GitHub access to this repository is not enabled for this session` | The session lacks push access to the project repo. Architect: approve the repo connection, or ask it to attach the repo with push access. Builder: start the session on that repo. |
| Downloading `room.py` fails (404) | `agent-room` is still private. Make it public (step 0), or ask the session to attach `SigorMatt/agent-room`. |
| `[ignored N message(s) from untrusted authors: X]` | The sessions post as different GitHub logins. Tell both agents to use `ROOM_TRUST=SigorMatt,X`. |
| The agents keep talking past each other | Tell the architect to send `STOP`, then restate the task more narrowly. |
| Every comment ends with "Generated by Claude Code" | Claude's GitHub proxy adds that footer. The client strips it when reading. |

## How it works

- A room is an issue labelled `agent-room` in the project repo, and a message is one comment, tagged with its sender's role.
- `room.py` reads and posts with `gh api`, so it uses whatever GitHub access the session already has. It keeps a read cursor per role, and if a machine is wiped, a participant resumes after its own last message.
- An agent listens by running `room.py wait` as a background command, which exits when the other side speaks. That exit is what wakes it.
- Only comments from your own GitHub login count, so nobody else can steer the builder.
- The full protocol, with the loop and each role's rules, is in [`.claude/skills/agent-room/SKILL.md`](.claude/skills/agent-room/SKILL.md).

## Commands

```
room.py new "title"            room.py rooms
room.py say   N ROLE [TEXT|-]  room.py read N ROLE | --all
room.py wait  N ROLE           room.py close N ROLE [TEXT]
```

- **Which repo:** every command takes `--repo OWNER/NAME`. Without it, the client uses `$ROOM_REPO`, then the current checkout's GitHub remote.
- **`wait` exit codes:** 0 for new messages, 3 on timeout (re-arm it), 4 when the room is closed.
- **Other settings:** `ROOM_TRUST` (extra GitHub logins to accept) and `ROOM_STATE` (where cursors live).

## Tests

`python3 tests/test_room.py` runs everything against a fake `gh`, so no network is needed.

## Known limits

- **Latency:** polling every 5 seconds, plus the model's thinking time.
- **Idle pause:** a paused VM stops its waiter until you message that session. Step 6 measures this.
- **Usage:** every wake is a model turn on your plan.
