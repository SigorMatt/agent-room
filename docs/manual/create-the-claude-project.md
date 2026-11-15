# Create the project's Claude Project

[All manuals](README.md)

## When to use it

Once per project, right after creating the repo. Every chat in this Claude Project acts as the project's architect.

## What you need first

- The repo ([Create the repo](create-the-repo.md)).
- The skill saved in this Claude account ([Save the skill, in each account](save-the-skill.md)).

## Steps

1. In the Claude app, open **Projects** and create a new one. Name it after the repo, for example `pet-todo`.
2. Open the Project's instructions and paste this, with `<repo>` replaced by the repo's name:

   ```text
   This Project is the architect's home for SigorMatt/<repo>, built with the agent-room pipeline. In every chat: load the agent-room skill and act as architect. The pipeline version and the current room are recorded in docs/playbook/PLAYBOOK.md on the agent-room/state branch.
   ```

3. Save.

## What you should see

- A new chat in this Project starts with "Operating as architect under agent-room `<version>`."

## If you don't

That first line is missing, so the rules didn't load. Check, in order:

1. The skill is saved and switched on in this account.
2. The instructions are pasted whole, with the right repo name.
3. agent-room is public.

Then start a new chat in the Project.
