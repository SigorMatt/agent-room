<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

1\. Superseded holds can still permit merges <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
<b><i>check_sensitive</i></b> accepts a trusted decision after a matching hold without checking whether that
decision says the hold was superseded, despite the new instruction to post clearing decisions that
allow nothing. If a newer hold follows only review-record changes, the older hold still passes the
head check, so supplying its clearing decision to <b><i>gate</i></b> or <b><i>merge --allow-hold 5</i></b> permits the
merge.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The new multi-hold workflow creates clearing decisions for older holds, but the gate can treat those decisions as merge authorization when only review records changed.

## Fix Focus Areas
- ARCHITECT.md[366-366]
- room.py[2563-2573]

## Recommended Fix
Make the gate reject an older hold's decision once a newer hold for the same PR supersedes it, while preserving the existing allowance for review-record-only changes after a hold that has not been superseded. Test a newer review-record-only hold followed by an older clearing decision, and remove or qualify the documentation's unconditional refusal claim.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/c9be4e47-fcd9-4321-ace0-834ae7359e70?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/c9be4e47-fcd9-4321-ace0-834ae7359e70)