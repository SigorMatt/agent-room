<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

2\. Watchdog loses its builder-progress signal <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
The watchdog rule in <b><i>v1.md</i></b> counts a builder push as progress, but the build-state decision removes
builder pushes. The watchdog therefore relies only on recorded-step changes, so a lead making real
progress through builders with no step change for three hours is reported as <b><i>LEAD-SILENT</i></b> and
buzzes Matthew.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The watchdog progress test in `docs/design/v1.md` (line 266) treats 'a builder pushed' as progress. `docs/design/BUILD-STATE.md` decides builders never push, so that signal is gone and the watchdog can only see recorded-step changes. A lead working through long builder tasks would be reported as silent.

## Fix Focus Areas
- docs/design/v1.md[266-266]
- docs/design/BUILD-STATE.md[66-66]

## Recommended Fix
Change the watchdog's progress signal to what still happens: recorded-step or MISSIONS.md changes, plus `STATUS` posts or commits to the state branch. Then update the sentence about the watchdog catching a stuck lead to match.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/06313873-b12e-4dc5-b6de-c063c8fd2f55?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/06313873-b12e-4dc5-b6de-c063c8fd2f55)