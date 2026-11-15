# Set up the lead task

[All manuals](README.md)

## When to use it

Once per project, at its first kickoff, when the architect asks. Again only if you move the project to your other account.

The lead task is a scheduled task that starts each lead. The lead before starts it at a handover, the watchdog for a takeover, and the architect at kickoff and after your decision. Without it, you start every lead yourself.

Do this on a computer, in a browser. Only the web page makes the trigger and its token.

## What you need first

- The task's prompt, from the architect. It prints it for your repo with `python3 room.py lead-task-prompt --repo OWNER/NAME`.
- The `agent-room` cloud environment ([Create the `agent-room` cloud environment](create-the-cloud-environment.md)).
- The repo connected to Claude ([Connect GitHub](connect-github.md)).
- The Claude account the project runs in. The task and its token belong to that account.

## Steps

1. Open `https://claude.ai/code/routines` and click **New task**.
2. **Name:** filled in with your repo:

   ```text
   agent-room lead SigorMatt/<repo>
   ```

3. **Prompt:** paste the architect's prompt, whole and unchanged.
4. **Trigger:** choose **API**, with no schedule. The token is made when you click **Create** (step 7).
5. Open **Advanced settings**, then **General**:
   - **Repository:** `SigorMatt/<repo>`.
   - **Cloud environment:** `agent-room`. It isn't the default, so pick it.
6. Still in **Advanced settings**:
   - **Connectors:** remove all of them.
   - **Behavior:** turn **Auto-fix** off.
   - **Notifications:** off. The pipeline buzzes you through ntfy itself.
7. Click **Create**.
8. Copy the token at once. It's shown only once. Don't paste it into a chat, the room or a file.
9. Add the token to the `agent-room` environment:
   1. Open the task's edit dialog, then **Advanced settings**, **General**, **Cloud environment**.
   2. Hover over `agent-room` and click its settings icon.
   3. Find **Environment variables**, and add this line, with your repo's `<NAME>` and the token:

      ```text
      ROOM_FIRE_TOKEN_<NAME>=<token>
      ```

   4. Click **Save changes**.

   `<NAME>` is the repo's name, without `SigorMatt/`, in capitals, with every character other than a letter or a digit turned into `_`. For `pet-todo` the line starts `ROOM_FIRE_TOKEN_PET_TODO=`. Each project has its own line, so the environment can hold several.
10. Tell the architect:

    ```text
    The lead task is set up.
    ```

    It finds the task itself and records its ID in the playbook. Never give it the token.

Why a variable and not a network secret: leads send the token to `api.anthropic.com`, and the environment never attaches network secrets to that site. So it must be a variable, which every session in the environment can read. That is acceptable because the token can only start this one task, and the task's prompt accepts nothing but a well-formed join line for this repo.

## What you should see

- The task `agent-room lead SigorMatt/<repo>` in the list at `https://claude.ai/code/routines`, with an API trigger and no schedule.
- `ROOM_FIRE_TOKEN_<NAME>` among the `agent-room` environment's variables.
- The architect records the task and starts the first lead ([Kick off a phase and start its first lead](kick-off-a-phase.md)).

## If you don't

- No **API** trigger: you're in the app. Use a browser on a computer.
- `agent-room` isn't in the **Cloud environment** list: create it first ([Create the `agent-room` cloud environment](create-the-cloud-environment.md)).
- The repo isn't in the **Repository** list: [Connect GitHub](connect-github.md).
- You lost the token before saving it, and no lead has run from the task yet: delete the task and create it again from step 1. Once leads have run from it, never delete it: deleting a task deletes the sessions it started. Ask the architect instead.
- Later, a `NEXT-LEAD-NEEDED` says `not configured` or `token rejected`, or preflight warns `lead task not configured`: the variable is missing, misspelt, or holds an old token. Check the line from step 9. A lead reads the variables when it starts, so the fix reaches the next lead. Then answer the buzz ([Answer a buzz](answer-a-buzz.md)).
