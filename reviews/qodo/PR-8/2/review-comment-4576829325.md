<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

2\. Some recent merges trigger stall alarms <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
<b><i>mission_merge</i></b> examines only the first 100 closed pull requests sorted by update time. If
subsequent updates place at least 100 other closed requests ahead of a recent mission merge, the
watchdog omits that merge from progress and can alarm despite the completed work.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The watchdog can miss a recent mission merge outside the first page of closed pull requests.

## Fix Focus Areas
- room.py[2830-2842]
- room.py[3071-3078]

## Recommended Fix
Page through closed pull requests until the relevant merge window has been covered, rather than filtering only the first response. Test with a mission merge displaced by more than 100 subsequently updated closed requests.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/94851ad7-2766-4bad-bd06-8f4ae2a2d00d?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/94851ad7-2766-4bad-bd06-8f4ae2a2d00d)