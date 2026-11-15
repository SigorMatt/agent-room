<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

4\. One lead can hide messages from another <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
<b><i>unseen</i></b> now distinguishes leads by session, but <b><i>cursor_file</i></b> still stores one cursor per room and
role. When two lead sessions share a machine, the first lead&#x27;s read advances the second lead&#x27;s
cursor past architect messages that the second has not seen.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Two sessions of the same role share a cursor even though messages are now hidden per session.
## Fix Focus Areas
- room.py[266-288]
- room.py[302-326]
## Recommended Fix
Key read and wait cursors by room, role, and validated session ID. Update cursor moves and reads consistently, with a deliberate migration path for existing role-only cursors.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/4e50d753-0bf1-49c3-ba5e-45f3a02c30f0?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/4e50d753-0bf1-49c3-ba5e-45f3a02c30f0)