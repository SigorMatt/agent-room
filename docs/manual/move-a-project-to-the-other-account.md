# Move a project to the other account

[All manuals](README.md)

## When to use it

You want a project to run on your other Claude account, for example because usage on this one is running low.

## What you need first

In the other account, once:

- the skill saved ([Save the skill, in each account](save-the-skill.md));
- GitHub connected ([Connect GitHub](connect-github.md));
- the `agent-room` environment, with the same variables, websites and secrets ([Create the `agent-room` cloud environment](create-the-cloud-environment.md), [Set up environment needs](set-up-environment-needs.md));
- a Claude Project for this repo, with the same instructions ([Create the project's Claude Project](create-the-claude-project.md)).

## Steps

1. In the old account's architect chat, send, and wait for the `PAUSED` buzz:

   ```text
   Pause the lead: moving to the other account.
   ```

2. In the same chat, with the room number:

   ```text
   Delete the watchdog task for room N, then wrap up the session.
   ```

3. In the old account, archive the lead session in the Code tab, and stop using that architect chat.
4. In the other account, start a new chat in the project's Claude Project. Check its first line, then send:

   ```text
   We moved this project from my other account. Create the watchdog for room N as at kickoff (ARCHITECT.md section 8, steps 4 and 5), then give me the join line.
   ```

5. Start the lead in the other account ([Start the next lead by hand](start-the-next-lead-by-hand.md)).

## What you should see

- The new chat's first line: "Operating as architect under agent-room `<version>`."
- A new `watchdog:` line in `PLAYBOOK.md`.
- `LEAD ONLINE` in the room within about 10 minutes, from the session in the other account.

## If you don't

- The old watchdog wasn't deleted: in the old account, open the scheduled task named `agent-room watchdog SigorMatt/<repo> room N` and delete it. Delete only that one: deleting a lead's task deletes its session.
- The new lead can't reach the repo: [Connect GitHub](connect-github.md) in that account.
