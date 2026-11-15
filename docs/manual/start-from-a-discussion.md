# Start from a discussion

[All manuals](README.md)

## When to use it

You already discussed the project in an ordinary Claude chat, outside its Claude Project, and there's no code yet. The old chat writes a digest, then the design continues in the Project.

## What you need first

- The repo ([Create the repo](create-the-repo.md)) and its Claude Project ([Create the project's Claude Project](create-the-claude-project.md)).
- The old discussion chat.

## Steps

1. In the old discussion chat, send, filled in:

   ```text
   Load the agent-room skill and act as architect for SigorMatt/<repo>, starting from this discussion (ARCHITECT.md section 5.2): write and commit the digest.
   ```

2. If that chat doesn't have the skill, send this instead:

   ```text
   Read https://raw.githubusercontent.com/SigorMatt/agent-room/main/STABLE, then read ARCHITECT.md from SigorMatt/agent-room at that version, in full. Act as architect for SigorMatt/<repo>, starting from this discussion (section 5.2): write and commit the digest.
   ```

3. Approve the repo when Claude asks. Wait for: "Digest committed. Continue in a fresh chat in the project's Claude Project."
4. Start a new chat in the project's Claude Project and send:

   ```text
   Continue SigorMatt/<repo> from the digest of our discussion.
   ```

5. Settle the open questions and contradictions it brings up. Then continue as in [Start from scratch](start-from-scratch.md), step 3.

## What you should see

- `docs/playbook/DIGEST.md` on the `agent-room/state` branch, with four headings: Decisions, Contradictions, Open questions, Can't verify.
- The new chat's first line, "Operating as architect under agent-room `<version>`.", then a summary of the digest.

## If you don't

- The old chat doesn't start with "Operating as architect…": it didn't load the rules. Send the line in step 2.
- The old chat keeps designing: that's for the Project chat. Tell it to commit the digest and stop.
- The new chat doesn't find the digest: send `check the state branch for DIGEST.md`, and check the branch on GitHub ([Read the design and state on the state branch](read-the-state-branch.md)).
