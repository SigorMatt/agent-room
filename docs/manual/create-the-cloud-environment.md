# Create the `agent-room` cloud environment

[All manuals](README.md)

## When to use it

Once, before your first project, in each Claude account that will run leads. Leads and the watchdog run in this environment. It holds your ntfy topic, the Qodo switch, and the websites a session may reach.

## What you need first

- Your ntfy topic ([Install ntfy and subscribe](install-ntfy-and-subscribe.md)).
- Whether the Qodo app reviews pull requests on your GitHub account: decides `on` or `off` below.
- A browser. This is easiest at claude.ai/code.

## Steps

1. Open `https://claude.ai/code`. Open the environment selector under the message box, then **New environment**.
2. **Name:** exactly

   ```text
   agent-room
   ```

3. **Network access:** **Custom**. Put this in **Allowed domains**, and tick **Also include default list of common package managers**:

   ```text
   ntfy.sh
   ```

4. **Environment variables:** paste these two lines, with your topic in the first. Use `QODO_REVIEW=off` if you don't use Qodo.

   ```text
   ROOM_NTFY_TOPIC=<your topic>
   QODO_REVIEW=on
   ```

5. Save.

Each project may add websites and secrets later ([Set up environment needs](set-up-environment-needs.md)). The environment is shared by all your projects.

## What you should see

- `agent-room` in the environment selector.
- Next: [Test the buzz](test-the-buzz.md).

## If you don't

- No **New environment** in the app: use a browser.
- A lead's checks later say `ROOM_NTFY_TOPIC is not set` or `QODO_REVIEW must be 'on' or 'off'`: fix the variable. Spell it exactly, with no spaces or quotes. A lead gets the variables when it starts, so the fix reaches the next lead.
