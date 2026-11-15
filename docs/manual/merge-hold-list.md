# Merge-hold list

[All manuals](README.md)

## When to use it

- To understand a `MERGE-HOLD-n` buzz.
- To choose, with the architect, which areas you always approve yourself.

## What you need first

- The hold message, `MERGE-HOLD-n: PR #<number>, reason <r> (…)`, or the playbook draft. A hold with several reasons names each: `reason 1, reason 5`.

## Steps

1. Find the reason. The lead merges its own pull request unless one of these applies:

   | Reason | Means |
   | --- | --- |
   | 1 | A decision only you can make is open: a top-severity finding without a fix, or a finding put off a second time |
   | 2 | A review used all its rounds with a finding still undecided |
   | 3 | Checks fail on the merge, and one fix attempt couldn't repair them |
   | 4 | The change reaches well outside the mission's plan |
   | 5 | It touches an area on the merge-hold list; the message names the files |
   | 6 | Qodo is on, but this pull request and the previous one got no Qodo review |

2. The default list (reason 5), which each project can change in `PLAYBOOK.md`:
   - CI and workflow files;
   - authentication, cryptography or secrets handling;
   - new dependencies;
   - destructive data migrations;
   - deleted or weakened tests.
3. To change the list: before kickoff, when you [Approve the playbook](approve-the-playbook.md); during a phase, through [Change something mid-build](change-something-mid-build.md). The architect writes each area as file patterns.
4. To answer a hold: [Answer a buzz](answer-a-buzz.md). "Merge as is" for reason 5 lets the lead merge that one pull request.

## What you should see

- The list under "Merge-hold list" in `PLAYBOOK.md`, one line per area with its file patterns.

## If you don't

- A hold for files you don't mind: answer "merge as is", and ask the architect to narrow the pattern for next time.
- A change you wanted held merged anyway: its files didn't match a pattern. Ask the architect to widen it ([Change something mid-build](change-something-mid-build.md)).
