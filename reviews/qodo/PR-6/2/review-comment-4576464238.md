<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

3\. Block repair erases mission records <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
<b><i>BROKEN_BLOCK</i></b> can span from a damaged opening fence to a later fence in the mission notes, and
<b><i>with_block</i></b> replaces that entire span with a restored block. If an outside edit also removes the
block&#x27;s closing fence, the next state write can delete intervening mission tables, tasks, and parked
questions from the pushed file.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Repairing a block with damaged fences can consume and delete mission records below it.
## Fix Focus Areas
- room.py[553-554]
- room.py[873-888]
## Recommended Fix
Do not replace text through an inferred later closing fence when the original boundary is uncertain. Prepend a valid canonical block and retire the damaged fence while preserving all existing prose.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/7d38122d-f06b-4503-8965-c5599c14d71e?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/7d38122d-f06b-4503-8965-c5599c14d71e)