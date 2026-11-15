<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

6\. Recovery strands unpushed state commits <code>🐞 Bug</code> <code>☼ Reliability</code>

<pre>
<b><i>ensure_worktree</i></b> moves a stale linked state worktree aside without checking whether it contains
local changes or unpushed commits. When it prunes and recreates the worktree at the original path,
the moved copy&#x27;s Git administrative link can point at the replacement, leaving its earlier commit
without a normal ref or reflog.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Rebuilding a stale linked worktree can strand commits and obscure local changes that were never pushed.
## Fix Focus Areas
- room.py[663-695]
- room.py[705-728]
## Recommended Fix
Detect and clearly report pending changes before recovery. Preserve the stale worktree's HEAD under a durable ref or standalone repository, and do not reuse its Git administrative entry until its local history is recoverable.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/74de7721-4ee0-4fbc-9c03-1ee968382deb?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/74de7721-4ee0-4fbc-9c03-1ee968382deb)