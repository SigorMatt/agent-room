# Test the buzz

[All manuals](README.md)

## When to use it

Once, after creating the cloud environment, and whenever buzzes seem to have stopped.

## What you need first

- The `agent-room` cloud environment ([Create the `agent-room` cloud environment](create-the-cloud-environment.md)).
- The ntfy app subscribed to your topic.
- agent-room public.

## Steps

1. In the Claude app, open the **Code** tab and start a new session: any repository, environment `agent-room`.
2. Send:

   ```text
   Run these two commands and show me what the last one prints:
   curl -fsSL https://raw.githubusercontent.com/SigorMatt/agent-room/main/room.py -o room.py
   python3 room.py ping
   ```

3. Archive the session afterwards.

## What you should see

- Your phone buzzes: **agent-room test**, "If your phone buzzed, agent-room notifications work."
- The session prints `buzz sent - check your phone`.

## If you don't

| The session prints | Fix |
| --- | --- |
| `ROOM_NTFY_TOPIC is not set` | The session isn't in the `agent-room` environment, or the variable is missing from it |
| `buzz failed: … 403 …` | `ntfy.sh` isn't in the environment's allowed domains |
| `buzz failed: … 429 …` | ntfy's daily limit: [Handle ntfy limit errors](handle-ntfy-limit-errors.md) |
| `buzz sent`, but the phone stays quiet | The topic in the app doesn't match the variable exactly, or Android restricts ntfy's battery use |
| A 404 when downloading `room.py` | agent-room is still private ([Make agent-room public](make-agent-room-public.md)) |
