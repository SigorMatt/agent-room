# Install ntfy and subscribe

[All manuals](README.md)

## When to use it

Once, before your first project. Buzzes reach your phone through the ntfy app.

## What you need first

- Your phone.
- A way to make a long random name, such as your password manager's generator. Don't ask a Claude chat for one: the name must stay out of chats.

## Steps

1. Install **ntfy** from Google Play, F-Droid or the App Store.
2. Make up your topic: `agentroom-` followed by at least 16 random letters and digits. Save it in your password manager.
3. In the ntfy app, tap **+**, enter the topic, keep the server `ntfy.sh`, and subscribe. You don't need an account.
4. On Android, turn on instant delivery if the app offers it, and let ntfy run without battery restrictions.

Keep the topic private. Anyone who knows it can read your buzzes. A buzz carries only the message kind, the project and the room number, such as `ESCALATION-3 · pet-todo room 1`, never the content. Still, put the topic only in two places: the ntfy app and the `agent-room` cloud environment. Never in a chat, a room, an issue or a file.

## What you should see

- Your topic in the ntfy app's list, with no messages yet. The first one comes from [Test the buzz](test-the-buzz.md).

## If you don't

- The app asks for a server: keep `ntfy.sh`, the default.
- You think the topic leaked: make a new one, subscribe to it, and change `ROOM_NTFY_TOPIC` in the cloud environment ([Create the `agent-room` cloud environment](create-the-cloud-environment.md)). Then unsubscribe from the old one.
