# Move a project to the other account

[All manuals](README.md)

## When to use it

You want a project to run on your other Claude account, for example because usage on this one is running low.

## What you need first

In the other account, once:

- the skill saved ([Save the skill, in each account](save-the-skill.md));
- GitHub connected ([Connect GitHub](connect-github.md));
- the `agent-room` environment, with the same variables, websites and secrets ([Create the `agent-room` cloud environment](create-the-cloud-environment.md), [Set up environment needs](set-up-environment-needs.md));
- a Claude Project for this repo, with the same instructions ([Create the project's Claude Project](create-the-claude-project.md));
- a computer browser for step 5: the lead task can't move, so you create a new one there.

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
   We moved this project from my other account (ARCHITECT.md 9.8). Create the watchdog for room N as at kickoff (section 8, steps 4 and 5), set up the lead task again (step 6), then start a lead.
   ```

5. When it asks, set up the lead task in the other account ([Set up the lead task](set-up-the-lead-task.md)). Its token goes into that account's `agent-room` environment, under the same name.
6. The architect starts the lead with a starter task; approve its pop-up. If it can't, it gives you the join line: start the lead in the other account ([Start the next lead by hand](start-the-next-lead-by-hand.md)).

## What you should see

- The new chat's first line: "Operating as architect under agent-room `<version>`."
- New `watchdog:` and `lead-task:` lines in `PLAYBOOK.md`.
- `LEAD ONLINE` in the room within about 10 minutes, from the session in the other account.

## If you don't

- The old watchdog wasn't deleted: in the old account, open the scheduled task named `agent-room watchdog SigorMatt/<repo> room N` and delete it. Delete only that one, never the lead task: deleting a task deletes the sessions it started.
- The new lead can't reach the repo: [Connect GitHub](connect-github.md) in that account.
