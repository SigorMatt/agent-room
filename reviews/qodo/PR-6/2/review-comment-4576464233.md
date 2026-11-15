<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

2\. A damaged block restores an old lead <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
<b><i>STATE_BLOCK</i></b> can treat a later fence as the missing closing fence, and <b><i>read_block</i></b> accepts the
first parseable matching block even if it is a quoted copy below the real one. After an outside edit
damages either fence, an old lease copied into mission notes can become authoritative without a
warning, allowing a superseded lead to post, close the room, or reuse a counter.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Malformed fences or a quoted second block can make the current state appear to grant the lease to a superseded lead.
## Fix Focus Areas
- room.py[553-554]
- room.py[839-850]
- room.py[941-965]
## Recommended Fix
Require one canonical machine block in the expected position, with a correctly closed fence and only valid body lines. Reject ambiguous or damaged tips so lease reads fall back to the last valid commit; refuse duplicate blocks on commit.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/27a2daf3-2852-442d-9730-c64c93919820?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/27a2daf3-2852-442d-9730-c64c93919820)