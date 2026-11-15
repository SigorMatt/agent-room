<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

7\. A lead inside stale state cannot recover <code>🐞 Bug</code> <code>☼ Reliability</code>

<pre>
<b><i>ensure_worktree</i></b> rebuilds a stale state directory while Git commands and checkout discovery still
depend on the invoking directory. When a lead runs a state command from inside a state worktree
whose branch was recreated, clone-mode recovery can refuse it and linked-worktree recovery can fail
partway through after moving it.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The stale-worktree rebuild path does not work when the process is running inside the directory being replaced.
## Fix Focus Areas
- room.py[624-642]
- room.py[671-698]
## Recommended Fix
Resolve and retain a valid project repository or remote before moving the stale directory. Run recovery Git operations from that stable location, and recognize the candidate state directory independently of the invoking cwd.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/cde6b694-ee4e-4b1f-bb4b-9736f2f0ae03?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/cde6b694-ee4e-4b1f-bb4b-9736f2f0ae03)