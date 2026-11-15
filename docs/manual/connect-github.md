# Connect GitHub

[All manuals](README.md)

## When to use it

Once in each Claude account, before your first project. Chats and cloud sessions reach GitHub as you through this connection.

## What you need first

- Your GitHub login, `SigorMatt`.
- The Claude app, signed in to the account.

## Steps

1. In the Claude app, open the **Code** tab. On first use it asks you to connect GitHub. Sign in and authorize.
2. When GitHub asks where to install the Claude GitHub app, choose **All repositories**. If you choose **Only select repositories**, you'll add every new project repo by hand ([Create the repo](create-the-repo.md), step 4).
3. In Claude's settings, open **Connectors** and check that GitHub is connected. Chats use this.
4. Switch to your other Claude account and repeat.

## What you should see

- When you start a new session in the Code tab, the repository picker lists your repos.
- When an architect chat needs a repo, Claude asks you to approve access to it. After you approve, it can read and push.

## If you don't

- A repo is missing from the Code tab: on GitHub, open your **Settings**, then **Applications**, then **Configure** next to the Claude app, and add the repo.
- A session says `GitHub access to this repository is not enabled for this session`. In an architect chat: approve the repo when Claude asks, or reconnect GitHub under **Connectors**. For a lead: start the session on that repo.
