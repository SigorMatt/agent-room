<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

8\. Preflight can report no admin bypass when it couldn't read the ruleset <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
<b><i>cmd_preflight</i></b> stores <b><i>{}</i></b> for a failed or non-dict ruleset-detail response without recording that
the ruleset could not be inspected. When branch rules identify that ruleset, the bypass check finds
no actors in the empty dictionary and can print <b><i>✓ admin bypass: none</i></b> instead of an unknown
warning, because its existing error path covers only protection and branch-rules requests.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
A failed or non-dict ruleset-detail response is treated as though the ruleset has no bypass actors, allowing preflight to report `admin bypass: none` without inspecting it.

## Fix Focus Areas
- room.py[1238-1243]
- room.py[1267-1284]

## Recommended Fix
Track referenced rulesets whose detail requests return a non-200 status or a non-dict response in an `unreadable` list, separately from successfully read rulesets. When that list is non-empty, make the bypass check print `! admin bypass: unknown for <ruleset names> (report only)` instead of `✓ admin bypass: none`.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/344ffc3b-f7a2-46c9-8cdf-8b7374d70556?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/344ffc3b-f7a2-46c9-8cdf-8b7374d70556)