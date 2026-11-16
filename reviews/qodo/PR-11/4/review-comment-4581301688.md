<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

6\. Watchdog can take over from a working lead <code>🐞 Bug</code> <code>☼ Reliability</code>

<pre>
<b><i>cmd_watchdog</i></b> passes <b><i>takeover=lease_of(values)[0] != &quot;none&quot;</i></b> to <b><i>alarm_stage</i></b>, which calls
<b><i>watchdog_start</i></b> as soon as <b><i>silent_after</i></b> has passed since the last LEAD-STARTED or LEAD ONLINE.
Nothing checks whether the lease holder is still alive. Progress counts only step and pr changes,
mission-branch pushes and merges, so a live lead whose builders run past three hours with no merge
is enough to trigger it. The takeover lead runs <b><i>lease take --takeover</i></b> and the working lead loses
the lease mid-build. Before this PR the watchdog only alarmed, and the architect checked whether the
lead was alive before giving out a takeover line.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The watchdog starts a takeover lead as soon as `silent_after` has passed with no step, pr or branch progress. It does this even when the lease holder is alive and waiting on long-running builders, and the takeover takes the lease from a working lead.

## Fix Focus Areas
- room.py[2997-3039]
- room.py[3185-3196]

## Recommended Fix
Count the lease holder's recent trusted lead messages (for example any lead STATUS or other lead message from the lease holder's session) as a sign of a lead in `stall_episode`'s `sign`, or delay the first takeover start until one alarm interval after the first LEAD-SILENT. That gives a live lead the chance to answer with a STATUS, as LEAD.md asks. Add a test where the holder posts a STATUS after the alarm: the watchdog should not start a takeover.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/42dd4705-8671-4c77-a008-0f46c9491078?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/42dd4705-8671-4c77-a008-0f46c9491078)