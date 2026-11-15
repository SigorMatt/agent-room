<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

1\. The gate passes checks from the wrong app <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
<b><i>required_contexts()</i></b> discards the <b><i>app_id</i></b> attached to required checks, and <b><i>check_checks()</i></b>
matches results by context name alone. When a different app reports a successful check with that
name on HEAD, the gate can pass even though the configured app has not reported its required check.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Required check configurations can specify a GitHub App, but the gate drops that identity and accepts a same-named result from another app.
## Fix Focus Areas
- room.py[2194-2212]
- room.py[2238-2255]
- tests/test_gate.py[1079-1140]
## Recommended Fix
Preserve each required check's app ID and compare it with the reporting check run's app ID when evaluating required checks. Do not let a same-named result from another app satisfy an app-specific requirement; add a regression test for that case.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/5c879338-59e4-4678-8daf-290e3cf73f0d?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/5c879338-59e4-4678-8daf-290e3cf73f0d)