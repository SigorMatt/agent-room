<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

5\. Weakened tests evade the merge hold <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
The M3 gate specification says a merge-hold bullet containing <b><i>deleted</i></b> matches only deleted paths,
while the default playbook puts deleted and weakened tests in that same bullet. An edit to an
existing test therefore matches the test globs but does not trigger the sensitive-path hold required
by the governing design.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The deleted-only rule exempts modified tests from the default sensitive-path hold, including modifications that weaken them.
## Fix Focus Areas
- docs/design/m3-reviews-gate.md[108-109]
- templates/playbook/PLAYBOOK.md[27-31]
## Recommended Fix
Specify a conservative hold for modified tests unless a reliable weakened-test determination is available. Keep the template labels and gate matching rules aligned with that behavior.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/db26aaf6-31bd-4f77-bfc8-88567e336b51?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/db26aaf6-31bd-4f77-bfc8-88567e336b51)