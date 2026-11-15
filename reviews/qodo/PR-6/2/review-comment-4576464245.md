<img src="https://img.shields.io/badge/Low-634FD1?style=flat-square" height="20px" alt="Informational">

9\. Preflight --fix failure prints no reason <code>🐞 Bug</code> <code>◔ Observability</code>

<pre>
The <b><i>--fix</i></b> handler formats <b><i>{e or &#x27;the state branch moved; run it again&#x27;}</i></b>, but an exception object
is always truthy, so a bare <b><i>StateMoved()</i></b> (empty message) wins over the fallback. When the
lead-files push loses a race during <b><i>preflight --fix</i></b>, the output reads `lead-owned files: --fix
failed: ` with no explanation and no hint to retry.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Preflight `--fix` prints an empty reason when `StateMoved` is raised, because `e or '...'` tests the exception object, which is always truthy.

## Fix Focus Areas
- room.py[1335-1336]

## Recommended Fix
Replace `{e or 'the state branch moved; run it again'}` with `{str(e) or 'the state branch moved; run it again'}`, or catch `StateMoved` in its own `except` branch with that message.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/34971e39-52d9-4e93-967c-2d49f278cc08?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/34971e39-52d9-4e93-967c-2d49f278cc08)