# Create the repo

[All manuals](README.md)

## When to use it

At the start of every new project, before anything else. The architect never creates repos. For an existing code repo, skip step 1 and do the rest.

## What you need first

- A name for the project.
- A choice of private or public:
  - **Private:** only you can read the room, the design and the reviews. On GitHub Free, a private repo can't have branch protection. That's fine: the checks accept it.
  - **Public:** anyone can read them, but only your login can steer the build.

## Steps

1. Create the repository under `SigorMatt`, in the GitHub app or a browser. **Add a README** is optional: an empty repo is fine, because the architect's first step (`state init`) makes the first commit.
2. In a browser, open its settings (desktop site if needed):

   ```text
   https://github.com/SigorMatt/<repo>/settings
   ```

3. Under **General**, then **Pull Requests**: tick **Automatically delete head branches**, and leave **Allow merge commits** ticked. Agents can't delete branches, so without this every merged mission branch stays behind.
4. If the Claude GitHub app, or Qodo, has access to selected repositories only, add this repo to both: your GitHub **Settings**, then **Applications**, then **Configure**.
5. Branch protection is optional. If you protect `main`: keep required status checks and force-push protection, but require no approving reviews. Add no rule or ruleset that covers `mission/*` or `agent-room/state`.

## What you should see

- **Automatically delete head branches** ticked in the settings.
- The repo in the Code tab's repository picker.

## If you don't

- The repo isn't in the Code tab: step 4.
- You skipped step 3 and old `mission/…` branches pile up: tick it now, then delete the merged ones on `https://github.com/SigorMatt/<repo>/branches` with the bin icon. Never delete `main` or `agent-room/state`.
