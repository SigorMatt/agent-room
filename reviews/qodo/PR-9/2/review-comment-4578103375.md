<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

1\. Survey tests can expose project credentials <code>🐞 Bug</code> <code>⛨ Security</code>

<pre>
<b><i>briefs/survey.md</i></b> tells the survey subagent to install repository-declared dependencies and run the
repository&#x27;s test command without first isolating that execution from its credentials. When an
existing project&#x27;s checkout contains a malicious install hook or test script, that code runs in the
architect&#x27;s cloud environment, which can contain project secrets and authenticated GitHub access.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The survey runs repository-controlled install hooks and tests in an environment that may hold project credentials.
## Fix Focus Areas
- briefs/survey.md[15-28]
- ARCHITECT.md[130-138]
## Recommended Fix
Require the architect to run survey installs and tests in a disposable environment without GitHub authentication or project secrets, with restricted network access. Have the survey report tests as unverified when that isolation is unavailable.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/bef7ab1b-cc5b-40f1-a954-1bca80fe6811?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/bef7ab1b-cc5b-40f1-a954-1bca80fe6811)