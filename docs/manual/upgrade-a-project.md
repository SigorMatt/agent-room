# Upgrade a project

[All manuals](README.md)

## When to use it

A new agent-room release is out and you want a project to use it. Releases are tags such as `v1.0.1`. Each project stays on its pinned version until you upgrade it.

## What you need first

- The release's kind, from its entry in agent-room's changelog: a **patch** (`v1.0.x`), or a **minor or major** release.

  ```text
  https://github.com/SigorMatt/agent-room/blob/main/CHANGELOG.md
  ```

- The architect chat in the project's Claude Project.

## Steps

### Patch (`v1.0.x`): nothing pauses

1. Send, with the version:

   ```text
   Bump the pin to <version>. It's a patch release.
   ```

2. The architect updates the playbook's `pipeline:` line and the watchdog task. The next mission's lead picks it up. A mission held by a pipeline fault picks it up at once: the architect's `DECISION` tells its lead to re-download.

### Minor or major: the full procedure

1. Send, and wait for the `PAUSED` buzz:

   ```text
   Pause the lead: upgrade to <version>.
   ```

2. In the same chat:

   ```text
   Wrap up the session, bump the pin to <version>, and run your migration steps from the changelog.
   ```

3. If the changelog says so: re-save the skill ([Save the skill, in each account](save-the-skill.md)), and edit the Project's instructions.
4. Archive the old lead session in the Code tab, and stop using this architect chat.
5. Start a new chat in the project's Claude Project. Its first line names the new version.
6. Ask it for the normal join line and start a lead ([Start the next lead by hand](start-the-next-lead-by-hand.md)). The new lead runs its own migration steps.

## What you should see

- `pipeline: <version>` at the top of `PLAYBOOK.md` ([Read the design and state on the state branch](read-the-state-branch.md)).
- The next lead's first line, and after a full upgrade the new chat's first line, name `<version>`.
- After a full upgrade: `LEAD ONLINE` in the room within about 10 minutes.

## If you don't

- A first line still names the old version: ask the architect to check the `pipeline:` line of `PLAYBOOK.md`.
- No `PAUSED` buzz after about 35 minutes: [STOP or PAUSE](stop-or-pause.md), "If you don't".
