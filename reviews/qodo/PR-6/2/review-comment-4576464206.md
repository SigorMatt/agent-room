<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

1\. Recovery can move the project checkout <code>🐞 Bug</code> <code>☼ Reliability</code>

<pre>
<b><i>is_stale_state_worktree</i></b> identifies the project checkout through the process&#x27;s current directory
rather than the directory it is about to move. If <b><i>ROOM_STATE_DIR</i></b> names a detached project checkout
and the command runs from elsewhere, <b><i>ensure_worktree</i></b> can rename that checkout and replace its path
with a state worktree, disrupting linked builder worktrees.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Stale-directory recovery can mistake the project checkout for a disposable state worktree when invoked outside that checkout.
## Fix Focus Areas
- room.py[624-660]
- room.py[671-695]
## Recommended Fix
Inspect the candidate directory's own Git metadata to distinguish the project's main checkout from a managed state worktree, regardless of the invoking directory. Refuse uncertain directories before renaming or resetting them.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/6227fd32-dd73-49e5-8a3b-913e36e8edc4?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/6227fd32-dd73-49e5-8a3b-913e36e8edc4)