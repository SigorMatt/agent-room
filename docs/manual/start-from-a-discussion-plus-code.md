# Start from a discussion plus code

[All manuals](README.md)

## When to use it

You discussed the project in an old chat, and the repo already has code. The architect surveys the code and settles with you where it disagrees with the discussion.

## What you need first

- The repo with its code on `main`, with steps 2 to 5 of [Create the repo](create-the-repo.md) done.
- Its Claude Project ([Create the project's Claude Project](create-the-claude-project.md)), and the old discussion chat.

## Steps

1. Do steps 1 to 3 of [Start from a discussion](start-from-a-discussion.md).
2. Start a new chat in the project's Claude Project and send, filled in:

   ```text
   Continue SigorMatt/<repo> from the digest of our discussion. The repo already has code: run the survey first (ARCHITECT.md section 5.3).
   ```

3. It starts a survey helper, which lists what the code has, then shows you where the discussion and the code disagree. Decide each one; it records your answers in `DESIGN.md`.
4. It writes a "Phase 0" into the playbook: what exists and the known debt. If the tests don't pass on `main`, the first item becomes making them pass.
5. Continue as in [Start from scratch](start-from-scratch.md), step 3.

## What you should see

- `DIGEST.md` and `SURVEY.md` under `docs/playbook/` on the `agent-room/state` branch.
- A `D-n` entry in `DESIGN.md` for each disagreement you settled.
- The playbook's "Phase 0 known debt" filled in. The first lead turns that debt into to-dos for phase 1.

## If you don't

- The survey takes a while on a big repo. Wait for it.
- The chat says it can't start the survey helper: [Report a pipeline problem](report-a-pipeline-problem.md).
