<h3>PR Summary by Qodo</h3>

Document lead recovery after container restarts

<!-- qodo-describe-risk-badge -->
<!-- /qodo-describe-risk-badge -->
<code>📝 Documentation</code> <code>🕐 20-40 Minutes</code>

<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">

<details>
<summary>AI Description</summary>

<dl>
<dd>
<br/>

><pre>
>• Give leads a recovery procedure for stopped agents and commands after container restarts.
>• Preserve completed work and exclude restart interruptions from failed-attempt counts.
>• Record B-7’s completion and explain the restart status to owners.
></pre>

</dd>
</dl>

</details>

<!-- qodo-describe-risk-slot -->

<details>
<summary>Diagram</summary>

<dl>
<dd>

<br/>

```mermaid
graph TD
  Notice["Restart notice"] --> Room["Read room"] --> Worktrees["Inspect worktrees"] --> Choice{"Transcript available?"} --> Resume["Resume agent"] --> Checks["Rerun checks"] --> Status["Post STATUS"]
  Choice --> Fresh["Brief fresh agent"] --> Checks
```

</dd>
</dl>

</details>




<details>
<summary>High-Level Assessment</summary>

<dl>
<dd>

<br/>

>The documentation-only protocol fits an event that wakes the lead while leaving the room, lease, and state intact. Changing room.py or automatically resetting state would add risk without addressing the stopped subagents and commands the lead must assess.

</dd>
</dl>

</details>

<details>
<summary> Files changed (5) <code> +80 / -5 </code> </summary>

<dl>
<dd>

<br/>

<details>
<summary>Documentation (5) <code> +80 / -5 </code></summary>

<dl>
<dd>

<details>
<summary>CHANGELOG.md<code>Record M6e restart recovery</code> <code>+1/-0</code></summary>

<br/>

>Record M6e restart recovery
>
><pre>
>• Adds a release note describing the lead’s recovery procedure and clarifying that a container restart does not count as a failed attempt.
></pre>
>
><a href='https://github.com/SigorMatt/agent-room/pull/15/files#diff-06572a96a58dc510037d5efa622f9bec8519bc1beab13c9f251e97e657a9d4ed'>CHANGELOG.md</a>

</details>

<details>
<summary>LEAD.md<code>Define the lead’s post-restart procedure</code> <code>+20/-3</code></summary>

<br/>

>Define the lead’s post-restart procedure
>
><pre>
>• Directs the lead to read the room, inspect stopped agents’ worktrees, resume or replace agents, rerun interrupted waits, and post a status without repeating completed work. Clarifies attempt accounting and links the delegation rule to this procedure.
></pre>
>
><a href='https://github.com/SigorMatt/agent-room/pull/15/files#diff-0d7d95c154bdf0eaee1f65e13b353b2c0c4950ddce9c78849fbf72025b313c79'>LEAD.md</a>

</details>

<details>
<summary>BUILD-STATE.md<code>Track M6e and mark B-7 complete</code> <code>+4/-2</code></summary>

<br/>

>Track M6e and mark B-7 complete
>
><pre>
>• Adds the M6e milestone and assumption A-13, connects finding W to the new spec, and records B-7 as done.
></pre>
>
><a href='https://github.com/SigorMatt/agent-room/pull/15/files#diff-eb974eadcb2e1d4f382c2409c07a470b3df0574298ed8eda187eb1a6d7b1375f'>docs/design/BUILD-STATE.md</a>

</details>

<details>
<summary>m6e-restarts.md<code>Specify the M6e restart-recovery scope</code> <code>+54/-0</code></summary>

<br/>

>Specify the M6e restart-recovery scope
>
><pre>
>• Documents what survives and stops during a container restart, the intended lead procedure, and the work excluded from this docs-only change.
></pre>
>
><a href='https://github.com/SigorMatt/agent-room/pull/15/files#diff-b5cc2cefcb4d6374b27da69b65445359bb5f96a4f388b71441528fea150959a0'>docs/design/m6e-restarts.md</a>

</details>

<details>
<summary>troubleshooting.md<code>Explain restart statuses to owners</code> <code>+1/-0</code></summary>

<br/>

>Explain restart statuses to owners
>
><pre>
>• Adds a troubleshooting row explaining that a restart status requires no owner action because the room, lease, and state remain unchanged.
></pre>
>
><a href='https://github.com/SigorMatt/agent-room/pull/15/files#diff-bfec8ea3d3009f9d7d15f1153d8a9db48d7c0e60aa0343ad065af35765dbc2e4'>docs/manual/troubleshooting.md</a>

</details>

</dd>
</dl>

</details>

</dd>
</dl>

</details>

<!-- qodo-describe-head:0af3db83cd418073c7ecb8e49a50f5c9a318f710 -->