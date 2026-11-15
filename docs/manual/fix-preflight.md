# Fix preflight

[All manuals](README.md)

## When to use it

- At kickoff, when the architect shows you preflight lines marked `✗` (a failure) or `!` (a warning). It doesn't hand over until no `✗` is left.
- When a lead escalates a `✗` it can't fix itself.

## What you need first

- The preflight lines. The architect shows them; a lead quotes them in its `ESCALATION`.
- A browser for GitHub's settings and for claude.ai/code.

## Steps

1. Find each line below and do its fix.

   | The line says | Fix |
   | --- | --- |
   | `✗ push access` | Approve the repo when Claude asks, and check that the Claude GitHub app has it ([Connect GitHub](connect-github.md)). Remove any rule or ruleset that covers `mission/*` or `agent-room/state` |
   | `✗ main has no commits` | An empty repo. Send the architect the `state init` line below the table |
   | `✗ main requires approving reviews` | Repo **Settings**, then **Branches** (or **Rules**, then **Rulesets**): remove only the approving-review requirement. Keep required status checks and force-push protection |
   | `✗ approving reviews: can't read the rules` | Usually access: as for push access |
   | `! admin bypass` | Nothing. It's for information only |
   | `! … turn on 'Automatically delete head branches'` | Repo **Settings**, **General**, **Pull Requests**: tick it |
   | `✗ merge commits are not allowed` | Repo **Settings**, **General**, **Pull Requests**: tick **Allow merge commits**. The lead merges with a merge commit |
   | `! couldn't read allow_merge_commit` | Check that **Allow merge commits** is ticked there |
   | `✗ state branch lacks PLAYBOOK.md` or `DESIGN.md` | The architect commits them. For a new project, send it the `state init` line below the table |
   | `✗ … no pipeline version` or `… not a release tag` | The architect fixes the `pipeline:` line of `PLAYBOOK.md` |
   | `! … the pipeline is 'main'` | Fine until agent-room's first release, `v1.0.0` |
   | `✗ ROOM_NTFY_TOPIC is not set` (lead) | Add it to the `agent-room` environment ([Create the `agent-room` cloud environment](create-the-cloud-environment.md)) |
   | `✗ QODO_REVIEW must be 'on' or 'off'` (lead) | Set `QODO_REVIEW=on` or `QODO_REVIEW=off` there |
   | `✗ lead-owned files` (lead) | The lead fixes this itself. If it escalates it: [Report a pipeline problem](report-a-pipeline-problem.md) |

   The `state init` line:

   ```text
   Run state init.
   ```

2. At kickoff, tell the architect:

   ```text
   Fixed. Run preflight again.
   ```

3. For a lead's escalation, open the architect chat and send this, with what you fixed. It answers the lead.

   ```text
   Check the room. I fixed <what you fixed>.
   ```

## What you should see

- The last line reads `preflight passed: 0 failed, …`. Warnings (`!`) may remain.

## If you don't

- A line you don't recognise: send the architect

  ```text
  Explain this preflight line in plain words: <the line>
  ```

- A lead gets the environment's variables when it starts, so a variable you fix reaches the next lead.
