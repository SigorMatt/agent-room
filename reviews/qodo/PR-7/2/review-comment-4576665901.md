<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

2\. Qodo findings can have two dispositions <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
<b><i>check_dispositions()</i></b> adds each Qodo title to <b><i>seen</i></b> without rejecting a title already in the set.
When a dispositions table repeats a finding, both rows can pass validation and the gate reports
every finding decided despite the conflicting record.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The Qodo dispositions check accepts multiple rows for one finding, so a finding can have conflicting recorded dispositions.
## Fix Focus Areas
- room.py[2140-2153]
- tests/test_gate.py[1-1459]
## Recommended Fix
Before adding a normalized finding title to `seen`, report a disposition error if it is already present. Add a test with two otherwise valid rows for the same archived Qodo finding and assert that the gate fails.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/61970255-b735-4379-b46c-00130509ed8c?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/61970255-b735-4379-b46c-00130509ed8c)