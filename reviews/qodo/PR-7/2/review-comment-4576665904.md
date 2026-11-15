<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

3\. An edited hold releases paths nobody approved <code>🐞 Bug</code> <code>⛨ Security</code>

<pre>
<b><i>check_sensitive</i></b> reads the lead&#x27;s <b><i>MERGE-HOLD-&lt;n&gt;</i></b> text as it stands when the gate runs. It then
accepts any trusted <b><i>DECISION-&lt;n&gt;</i></b> whose comment id is larger than the hold&#x27;s, but editing a GitHub
comment keeps its id and <b><i>parse()</i></b> never reads <b><i>updated_at</i></b>. So if the lead edits an answered hold
to add a newly matched path, which is what the gate&#x27;s own &quot;doesn&#x27;t name X (the form: …)&quot; message
invites, the old decision passes for a path Matthew never saw. <b><i>RoomLog.answers</i></b> has the same gap
for top-severity owner decisions: an <b><i>ESCALATION-&lt;n&gt;</i></b> edited after the decision to name another
finding makes that decision cover it.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The gate links a DECISION to the lead's MERGE-HOLD/ESCALATION only by comparing comment ids. Edited comments keep their id, so an edit made after the decision changes what the decision appears to approve.

## Fix Focus Areas
- room.py[203-213]
- room.py[2324-2341]
- room.py[2405-2423]

## Recommended Fix
Have `parse()` also return `updated_at` (falling back to `created_at`). In `check_sensitive`, accept a decision only if the hold's `updated_at` is no later than the decision's `created_at`. In `RoomLog.answers`, accept only asks whose `updated_at` is earlier than the decision's `created_at`. When a hold was edited after its decision, say so in the failure and ask for a new hold and decision. Add a regression test where the fake gh returns an edited hold.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/c32315dd-5b03-47a5-bf4d-d13f46f1ba7d?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/c32315dd-5b03-47a5-bf4d-d13f46f1ba7d)