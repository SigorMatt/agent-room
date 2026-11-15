# Set up environment needs

[All manuals](README.md)

## When to use it

After you approve the playbook, when its "Environment needs" section lists websites or secrets. Before kickoff, and again whenever a change adds some.

## What you need first

- The list. Ask the architect:

  ```text
  What are the environment needs?
  ```

- The secrets themselves, such as API keys, from wherever you keep them. Never paste a secret into a chat, the room or a file.
- A browser at claude.ai/code.

## Steps

1. Open `https://claude.ai/code`, open the environment selector, and open the settings of the `agent-room` environment.
2. **Network access:** add each listed website to **Allowed domains**. Keep `ntfy.sh` and the package-manager default.
3. **Secrets:** add each under **Network secrets**, with the website it's for, the header it goes in, and its value. If the playbook doesn't name the header, ask the architect which one the service expects. Use an environment variable only if the playbook says there's no other way.
4. Tell the architect:

   ```text
   Environment needs are done.
   ```

The `agent-room` environment is shared by all your projects, so their websites add up.

## What you should see

- The websites under **Allowed domains**, and the secrets under **Network secrets**.
- The architect moves on to kickoff.

## If you don't

- A lead later can't reach a website: it escalates. Add the website, then answer the buzz ([Answer a buzz](answer-a-buzz.md)).
- A lead gets the environment when it starts. A change made while a lead runs reaches the next lead.
