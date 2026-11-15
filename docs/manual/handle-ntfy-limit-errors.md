# Handle ntfy limit errors

[All manuals](README.md)

## When to use it

A room message shows `[buzz failed: … 429 …]` or `(buzz failed: …)`, or a `STATUS` says a buzz failed, or messages that should buzz arrive in the room silently.

## What you need first

- The room on GitHub, to see what you missed.
- For a fix: a paid ntfy.sh plan, and a browser at claude.ai/code.

## Steps

1. Read the room. A failed buzz never stops a message: it's posted, only the buzz is lost. Answer anything you missed ([Answer a buzz](answer-a-buzz.md)).
2. Read the error:
   - **429:** ntfy.sh's daily limit, 250 messages per internet address. Cloud sessions share addresses with other users, so this can happen, though rarely. A free ntfy account changes nothing.
   - **403:** `ntfy.sh` isn't in the `agent-room` environment's allowed domains. Add it, and stop here.
3. If 429 keeps coming back, give the buzz your own limit:
   1. Subscribe to a paid ntfy.sh tier. In the ntfy web app, open **Account**, then **Access tokens**, and create a token. It starts with `tk_`.
   2. At claude.ai/code, open the `agent-room` environment's settings. Under **Network secrets**, add a secret: allowed websites `ntfy.sh`, a custom header named `Authorization`, prefix `Bearer`, the token as the value. Sessions never see it.
   3. Only if network secrets aren't available: add this environment variable instead.

      ```text
      ROOM_NTFY_TOKEN=tk_<your token>
      ```

4. [Test the buzz](test-the-buzz.md).

## What you should see

- The test buzz arrives, and later messages buzz again.

## If you don't

- The test prints another error: [Test the buzz](test-the-buzz.md), "If you don't".
- Still 429 with the token: check the secret's website is exactly `ntfy.sh`, and the header and prefix are spelled as above.
