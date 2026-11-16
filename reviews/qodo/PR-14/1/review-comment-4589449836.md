<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

2\. No automatic restart when a handover's successor dies <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
<b><i>start_after_alarm</i></b> treats any trusted <b><i>LEAD-STARTED</i></b> newer than <b><i>since</i></b> as the stall&#x27;s one start
(rule 2). On the ordinary path <b><i>since</i></b> is the last progress time, and <b><i>cmd_handoff</i></b> writes the step
before the outgoing lead runs <b><i>start-lead</i></b>, so the successor&#x27;s <b><i>LEAD-STARTED</i></b> is always newer than
that progress. The result is that a successor whose start didn&#x27;t take, or that joined and died
before its first step change or push, gets alarms and reminders but never the watchdog start. The
spec&#x27;s per-path list (&quot;released after a handover whose successor never came: one takeover or plain
start&quot;) and the CHANGELOG and ARCHITECT text all promise that start.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
On the ordinary-stall path, `start_after_alarm` counts the handover's own `LEAD-STARTED` (posted by role `lead` right after `handoff` writes the step) as the stall's one start. As a result, the watchdog never starts a lead when a handover's successor fails to join or dies before making progress. The spec says this path gets one start.

## Fix Focus Areas
- room.py[3033-3037]
- docs/design/m6d-watchdog.md[13-13]
- tests/test_m6d.py[1-438]

## Recommended Fix
Pick one of these and apply it everywhere:
- **Change the code to match the spec:** in rule 2, count only `LEAD-STARTED`s that aren't the handover's. For example, count only role `watchdog`/`architect` starts, or only starts newer than the first alarm of the stall. Then a lead-role `LEAD-STARTED` posted before the alarm doesn't use up the one start.
- **Change the docs to match the code:** remove the claim from the spec's per-path list, the CHANGELOG and ARCHITECT.md.

Either way, add a test: HANDOFF, then a lead `LEAD-STARTED`, then no LEAD ONLINE, then the stall alarm. Assert the intended outcome.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/30007175-bf9b-4263-ab3a-04b17ea93b75?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/30007175-bf9b-4263-ab3a-04b17ea93b75)