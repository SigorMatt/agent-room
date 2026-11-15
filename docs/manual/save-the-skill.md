# Save the skill, in each account

[All manuals](README.md)

## When to use it

Once in each Claude account you use, before your first project. Again only when a release's `CHANGELOG.md` says to re-save it. The skill tells a chat or a session which role to take and where to load the rules from.

## What you need first

- agent-room is public ([Make agent-room public](make-agent-room-public.md)).
- The Claude app, signed in to the account.

## Steps

1. Start a new chat, outside any Project, and send:

   ```text
   Read https://raw.githubusercontent.com/SigorMatt/agent-room/main/STABLE. Then fetch .claude/skills/agent-room/SKILL.md from SigorMatt/agent-room at that version, and offer it to me as a skill to save, exactly as it is.
   ```

2. Tap **Save** on the skill card it shows.
3. No card? On a computer: download `SKILL.md` from the repo's `.claude/skills/agent-room/` folder, put it in a folder named `agent-room`, zip that folder, and upload the zip under **Skills** in Claude's settings.
4. Switch to your other Claude account and repeat.

## What you should see

- `agent-room` in the skills list in Claude's settings, switched on.
- In a new chat, this question gets an answer about an architect and a lead working in a GitHub issue:

  ```text
  What does the agent-room skill do?
  ```

## If you don't

- The fetch fails with 404: agent-room is still private ([Make agent-room public](make-agent-room-public.md)).
- The skill is listed but off: switch it on.
- A chat in a project's Claude Project doesn't say "Operating as architect…": see [Create the project's Claude Project](create-the-claude-project.md).
