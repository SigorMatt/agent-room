# Make agent-room public

[All manuals](README.md)

## When to use it

Once, before your first project. Every session downloads `room.py` and the protocols from `SigorMatt/agent-room`. That works without giving each session access only if the repo is public.

## What you need first

- Your phone's browser, signed in to GitHub. The GitHub app doesn't show repository settings.

## Steps

1. Open this page. If you don't see **Settings**, switch the browser to the desktop site.

   ```text
   https://github.com/SigorMatt/agent-room/settings
   ```

2. Scroll to **Danger Zone**, tap **Change visibility**, choose **Public** and confirm.
3. Optional cleanup, in this repo only. Agents can't delete branches, so two test branches from the build are still there. Open the branches page and delete `mission/M0-probe` and `agent-room/state` with the bin icon:

   ```text
   https://github.com/SigorMatt/agent-room/branches
   ```

   Only in the agent-room repo. In a project repo, `agent-room/state` holds the whole design: never delete it there.

## What you should see

- The repo page shows **Public** next to its name.
- This link opens the code of `room.py` in a private browser tab, where you aren't signed in:

  ```text
  https://raw.githubusercontent.com/SigorMatt/agent-room/main/room.py
  ```

## If you don't

- The link shows `404: Not Found`: the repo is still private. Repeat step 2.
- **Change visibility** is greyed out: you're not signed in as `SigorMatt`.
