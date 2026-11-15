# Judge Qodo and switch it off

[All manuals](README.md)

## When to use it

- After about ten missions, to decide whether Qodo is worth its subscription.
- Any time you want to stop using it.

## What you need first

- `QODO-VALUE.md` on the state branch: one line per pull request ([Read the design and state on the state branch](read-the-state-branch.md)).
- For switching off: a browser at claude.ai/code.

## Steps

1. Read the file, or ask the architect:

   ```text
   Summarize QODO-VALUE.md: what did Qodo catch that the cold review didn't?
   ```

2. Read a line like this one:

   `PR #12 · same snapshot · first review: 7 findings, 4 already caught, 2 new (1 high, 1 low), 1 dismissed · rounds: 1 new · 6 min`

   - **same snapshot:** Qodo and the cold review saw the same code. Only these lines are a fair comparison.
   - **already caught:** the cold review found them too.
   - **new:** real problems only Qodo found, with their severity. This is what you pay for.
   - **dismissed:** Qodo was wrong. Noise.
   - **rounds:** findings on later fixes, counted apart. The last number is minutes to Qodo's first review.
3. Decide. One high-severity catch can justify the subscription; a pile of trivia can't. Nothing cancels by itself.
4. To switch it off: open the `agent-room` environment's settings at claude.ai/code and change the variable to:

   ```text
   QODO_REVIEW=off
   ```

5. Only then remove the Qodo app or cancel the subscription. With `QODO_REVIEW=on` and no Qodo, two pull requests in a row get no review, and the second is held.

## What you should see

- From the next lead on: `STATUS: PR #<n>: Qodo off` in the room, and `PR #<n> · Qodo off` lines in `QODO-VALUE.md`.

## If you don't

- A lead that was already running keeps the old setting. The next lead uses `off`.
- A `MERGE-HOLD` with reason 6 ("Qodo seems absent"): fix the Qodo app, or switch it off as in step 4, then answer the buzz ([Answer a buzz](answer-a-buzz.md)).
