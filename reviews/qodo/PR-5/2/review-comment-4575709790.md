<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

1\. Approved design says builders push, build state says they never do <code>🐞 Bug</code> <code>⚙ Maintainability</code>

<pre>
<b><i>v1.md</i></b> still makes builders push their task branches when done (Build step 2) and relies on that
for STOP recovery, while the <b><i>BUILD-STATE.md</i></b> decision table and Finding A say builders never push
and the lead merges worktree branches locally. A fresh session is told to read <b><i>v1.md</i></b> first and
then this file, so it can follow either instruction.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The approved design `docs/design/v1.md` says builders push their task branches (Build step 2, line 111) and that a running builder can push to its task branch on STOP (line 268). `docs/design/BUILD-STATE.md` records the decision 'Builders work in local worktrees and never push' (Finding A). A resuming session reads v1.md first and may follow the superseded process.

## Fix Focus Areas
- docs/design/v1.md[111-111]
- docs/design/v1.md[266-268]
- docs/design/BUILD-STATE.md[55-56]

## Recommended Fix
Edit v1.md so builders work in local worktrees and never push; the lead merges worktree branches locally. Update the STOP and PAUSE rules to match, and reword the 'pushes a task branch' references. Either record the change as an explicit CHANGE to the approved design or state in v1.md that BUILD-STATE supersedes it for the build.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/c5233d74-f7ee-467d-816c-44a7ea97bc09?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/c5233d74-f7ee-467d-816c-44a7ea97bc09)