<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

4\. Review exemption by directory lets code skip coverage <code>🐞 Bug</code> <code>⛨ Security</code>

<pre>
The coverage rule exempts everything under <b><i>reviews/</i></b> from review, decided by path rather than by
file type. Code placed under that directory would be merged with no review, and the gate would not
see it as a change needing coverage.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
`docs/design/v1.md` (line 143) exempts `reviews/` from coverage by directory alone. Review records are committed under `reviews/cold/M<k>/` and `reviews/qodo/PR-<n>/` (line 58). Any executable or source file placed under `reviews/` would merge without review, and `room.py gate` would not require coverage for it.

## Fix Focus Areas
- docs/design/v1.md[143-143]
- docs/design/v1.md[58-58]

## Recommended Fix
Define the exemption by file pattern (for example `reviews/**/*.md`) and state that any other path under `reviews/` is code. Have the gate treat non-report files under `reviews/` as changes that need coverage.
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

[Dismiss ↗](https://app.qodo.ai/findings/4e75349d-6191-4e19-b08d-bcaed96380b4?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/4e75349d-6191-4e19-b08d-bcaed96380b4)