# Start from scratch

[All manuals](README.md)

## When to use it

A new project with no earlier discussion and no code.

## What you need first

- The repo ([Create the repo](create-the-repo.md)) and its Claude Project ([Create the project's Claude Project](create-the-claude-project.md)).
- An idea of what to build.

## Steps

1. Start a new chat in the project's Claude Project and send, filled in:

   ```text
   New project: SigorMatt/<repo>. Let's design it. The idea: <what it should do, for whom, and anything you already know>.
   ```

2. Approve the repo when Claude asks for access.
3. Answer its design questions. It writes `DESIGN.md` and `PLAYBOOK.md` on the state branch as you go. It asks before settling anything that would otherwise come back to you as a buzz.
4. When it walks you through the playbook: [Approve the playbook](approve-the-playbook.md).
5. Then [Set up environment needs](set-up-environment-needs.md), and [Kick off a phase and start its first lead](kick-off-a-phase.md).

## What you should see

- The chat's first line: "Operating as architect under agent-room `<version>`."
- A branch `agent-room/state` in the repo, with `docs/playbook/PLAYBOOK.md` and `DESIGN.md`. On an empty repo, `main` also gets its first commit.

## If you don't

- No first line: the rules didn't load ([Create the project's Claude Project](create-the-claude-project.md), "If you don't").
- It can't reach the repo: approve access when asked, or see [Connect GitHub](connect-github.md).
- No `agent-room/state` branch after the design starts: send

  ```text
  Run state init.
  ```
