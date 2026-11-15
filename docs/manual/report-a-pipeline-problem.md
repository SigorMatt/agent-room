# Report a pipeline problem

[All manuals](README.md)

## When to use it

Something in agent-room itself went wrong, or a manual page left you with a question. Every question you have to ask counts as a manual bug: the page gets fixed.

## What you need first

- GitHub.
- The project, the room number, and the pipeline version: the `pipeline:` line of `PLAYBOOK.md`, or the version in a session's first line.

## Steps

1. Open:

   ```text
   https://github.com/SigorMatt/agent-room/issues/new
   ```

2. Title: what went wrong, in one line.
3. Body, filled in:

   ```text
   Project: SigorMatt/<repo>, room <N>
   Pipeline version: <version>
   Manual page and step: <page and step, or none>
   What I did: <…>
   What I expected: <…>
   What happened: <…, with links to the room message, pull request or session>
   ```

4. Don't add the `agent-room` label: it turns an issue into a room. Never include your ntfy topic, tokens or other secrets.

## What you should see

- The new issue in agent-room's **Issues**.

## If you don't

- No **New issue** button: issues are off for the repo. Turn them on under **Settings**, **General**, **Features**, **Issues**.
