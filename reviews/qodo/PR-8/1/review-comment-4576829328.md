<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

4\. Completed phases appear to need closing <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
<b><i>intent_hint</i></b> accepts a <b><i>DONE</i></b> closing note only when its timestamp is at or after <b><i>closed_at</i></b>. The
documented sequence posts <b><i>DONE</i></b> before closing; when the lead then uses <b><i>close</i></b> without another
<b><i>DONE</i></b> text, reconciliation calls the closed room unfinished and advises repeating the close.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Reconciliation rejects the documented DONE-then-close phase completion sequence.

## Fix Focus Areas
- room.py[3130-3146]
- docs/design/m5-protocols-manuals.md[29-32]

## Recommended Fix
Make the completion protocol and reconciliation agree: either recognize a trusted DONE posted immediately before the close, or prescribe one `close N lead "DONE: ..."` action rather than a separate DONE post followed by a default close. Test the exact documented command sequence.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/0479e9fb-4e15-4520-9f44-86593e3248aa?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/0479e9fb-4e15-4520-9f44-86593e3248aa)