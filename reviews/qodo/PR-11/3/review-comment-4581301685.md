<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

5\. A failed post-decision lead leaves the room silent forever <code>🐞 Bug</code> <code>☼ Reliability</code>

<pre>
<b><i>pending_decision</i></b> skips a <b><i>DECISION-n</i></b> as soon as any trusted <b><i>LEAD-STARTED</i></b> is newer than it.
After that, <b><i>cmd_watchdog</i></b> prints <b><i>quiet: step is waiting for owner…</i></b> on every later run, because
the step is still <b><i>waiting for owner</i></b> and the lease is still released. So if the lead started after
the decision (by the watchdog or the architect) never joins, for example because its session ended
at once, ran out of usage, or the fire returned 200 but the run died, the watchdog never alarms and
never starts another lead, and the room stalls with no buzz until someone reads it by hand.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
`pending_decision` treats any LEAD-STARTED after a DECISION as answering it for good. If that lead never posts LEAD ONLINE, the room stays at `waiting for owner` with the lease released, and the watchdog stays quiet forever.

## Fix Focus Areas
- room.py[3042-3062]
- room.py[3146-3159]

## Recommended Fix
In `pending_decision`, ignore a LEAD-STARTED after the decision when it is older than `STARTING_FOR` (or `a.silent_after`) and no trusted lead LEAD ONLINE follows it. Cap such retries, for example at two decision starts per DECISION, then post one LEAD-SILENT (within ALARM_CAP) saying the lead started after DECISION-n never joined. Add a test: parked room, DECISION older than 30 min, watchdog LEAD-STARTED older than 30 min with no LEAD ONLINE. The watchdog should start again or alarm, not stay quiet.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/8465c611-9314-4999-b33b-4e15f26bec79?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/8465c611-9314-4999-b33b-4e15f26bec79)