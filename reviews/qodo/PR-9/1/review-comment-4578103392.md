<img src="https://img.shields.io/badge/Low-634FD1?style=flat-square" height="20px" alt="Informational">

4\. Copied version line breaks the download urls <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
The architect&#x27;s version lookup runs <b><i>grep &#x27;^pipeline:&#x27;</i></b>, which prints the whole line (`pipeline:
v1.0.0<b><i>). The next step sets </i></b>V=&lt;version&gt;<b><i> without saying to strip the </i></b>pipeline:` prefix, which
room.py itself removes with <b><i>^pipeline:[ \t]*(\S+)</i></b>. If the line is used as is, both download URLs
point at a nonexistent ref and the protocol won&#x27;t load.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The skill's `grep '^pipeline:'` returns `pipeline: v1.0.0`, but `V` must be `v1.0.0` alone.

## Fix Focus Areas
- .claude/skills/agent-room/SKILL.md[22-24]

## Recommended Fix
Replace the grep with `sed -n 's/^pipeline:[[:space:]]*\([^[:space:]]*\).*/\1/p'` (or `awk '/^pipeline:/{print $2}'`) so the command prints only the version, matching room.py's own parse.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/ed3229ed-0d78-4b74-b632-494836d9e045?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/ed3229ed-0d78-4b74-b632-494836d9e045)