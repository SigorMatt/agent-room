<h3>Code Review by Qodo</h3>

<code>🐞 Bugs (0)</code>  <code>📘 Rule violations (0)</code>  <code>📜 Skill insights (0)</code>

<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">

<br/>

<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

<details>
<summary>  1.  <s>Unrecorded starts can spawn another lead</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/084270ed26cfbbcc6c03bb1dee191ea6da6acf54"><code>084270e</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>Docs and design spec now require retrying the LEAD-STARTED post up to 3 times, and state that a
>LEAD-STARTED (including an unconfirmed one) holds off any further start for 30 minutes, with the
>watchdog and architect told to wait for LEAD ONLINE rather than start another lead.
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ room.py[R3759-3763]</code> <code>●● Moderate</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>start_lead()</i></b> reports a successful fire even when <b><i>post_quietly()</i></b> fails to record <b><i>LEAD-STARTED</i></b>,
>leaving the watchdog without its record of the new session. If the next watchdog run occurs before
>that session posts <b><i>LEAD ONLINE</i></b>, it can fire another takeover for the same stall; the architect&#x27;s
>new instructions also treat an absent marker as a reason to start one by hand.
></pre>
></details>

<hr/>
</details>


<details>
<summary>  2.  <s>A retry can start two leads</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/3b98290d2452bbbc80ddf922331e440e4b2f236e"><code>3b98290</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>Unknown-outcome failures (timeouts, lost replies, HTTP 200 without routine_fire) are classified as
>possibly-started: start-lead posts &quot;LEAD-STARTED: unconfirmed (...)&quot; and exits 0 so callers don&#x27;t
>retry; definite failures still exit 1 for retry. Docs and the exit-code table were updated to
>match.&lt;/what_was_the_impact&gt;
>&lt;parameter name=&quot;relevant_diff_lines_start&quot;&gt;2832
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ room.py[R3768-3772]</code> <code>●● Moderate</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>start_lead()</i></b> returns exit 1 when <b><i>fire()</i></b> times out or receives a response it cannot recognize,
>even though the task may already have started a session. The handover instructions tell the lead to
>retry immediately, while no lease or <b><i>LEAD-STARTED</i></b> marker necessarily exists to stop the second
>fire.
></pre>
></details>

<hr/>
</details>


<br/>

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

<details>
<summary>  3.  <s>Buzz instructions can start a second lead</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/084270ed26cfbbcc6c03bb1dee191ea6da6acf54"><code>084270e</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>The LEAD-SILENT takeover section now states that one takeover lead is started in exactly one of two
>ways, never both: the architect starts it (Matthew does not start a lead himself), or the architect
>gives Matthew the takeover line to start. This removes the unconditional second start that could
>launch a duplicate takeover.
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ docs/manual/answer-a-buzz.md[R99]</code> <code>●●● Strong</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
>The revised <b><i>LEAD-SILENT</i></b> instructions say the architect may start the takeover itself or give
>Matthew a takeover line, but the next step tells Matthew to start a lead unconditionally. If the
>architect already fired the task, following both steps can launch another takeover instead of
>stopping after the first start.
></pre>
></details>

<hr/>
</details>


<details>
<summary>  4.  <s>Watchdog can take over from a working lead</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/d4cec85a78211e6c312baebea0a93038fca2fb75"><code>d4cec85</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>The diff makes the watchdog hold off takeover starts while any trusted lead message (including a
>STATUS) is within silent-after. The stall episode&#x27;s &quot;sign&quot; now includes trusted lead messages of any
>kind, and alarm_stage/start hold-off uses it. LEAD.md adds a rule to post STATUS before long steps.
>Also an alarm is still posted, but a live lead that posts is not taken over.
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ room.py[R3193-3195]</code> <code>●● Moderate</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>cmd_watchdog</i></b> passes <b><i>takeover=lease_of(values)[0] != &quot;none&quot;</i></b> to <b><i>alarm_stage</i></b>, which calls
><b><i>watchdog_start</i></b> as soon as <b><i>silent_after</i></b> has passed since the last LEAD-STARTED or LEAD ONLINE.
>Nothing checks whether the lease holder is still alive. Progress counts only step and pr changes,
>mission-branch pushes and merges, so a live lead whose builders run past three hours with no merge
>is enough to trigger it. The takeover lead runs <b><i>lease take --takeover</i></b> and the working lead loses
>the lease mid-build. Before this PR the watchdog only alarmed, and the architect checked whether the
>lead was alive before giving out a takeover line.
></pre>
></details>

<hr/>
</details>


<details>
<summary>  5.  <s>A failed post-decision lead leaves the room silent forever</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/69463dc02945084a02ed04bfb8ab45f3b0cbf662"><code>69463dc</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>N/A
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ room.py[R3057-3061]</code> <code>●● Moderate</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>pending_decision</i></b> skips a <b><i>DECISION-n</i></b> as soon as any trusted <b><i>LEAD-STARTED</i></b> is newer than it.
>After that, <b><i>cmd_watchdog</i></b> prints <b><i>quiet: step is waiting for owner…</i></b> on every later run, because
>the step is still <b><i>waiting for owner</i></b> and the lease is still released. So if the lead started after
>the decision (by the watchdog or the architect) never joins, for example because its session ended
>at once, ran out of usage, or the fire returned 200 but the run died, the watchdog never alarms and
>never starts another lead, and the room stalls with no buzz until someone reads it by hand.
></pre>
></details>

<hr/>
</details>


<details><summary><ins><strong>View medium (1)</strong></ins></summary><br/>
<details>
<summary>  6.  <s>Other processes can read the fire token</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/084270ed26cfbbcc6c03bb1dee191ea6da6acf54"><code>084270e</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>N/A
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ room.py[R3631-3633]</code> <code>●● Moderate</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>fire()</i></b> embeds the bearer token in the <b><i>curl</i></b> argument vector rather than passing it through a
>protected input channel. On a host where another local process can inspect process arguments during
>the request, that process can copy the credential used to fire the project&#x27;s lead task.
></pre>
></details>

<hr/>
</details>


</details>

<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">

<!-- qodo-self-review-slot -->


<!-- qodo-context:start -->
<details><summary><strong>Context sources</strong></summary>

<div>&#x2705; Context preparation</div>
<div>&nbsp;&nbsp;Commit messages: summarized; full text retained for this review</div>
<div>Review mode: <code>Auto: 🧠 Deep</code>: Dense orchestration changes span watchdogs, task triggers, leases, tokens, and many independent paths.</div>
<!-- qodo-context:end -->
</details>

<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">



<!-- qodo-daily-tip:start -->

<details>
<summary><strong>Tip of the day</strong></summary>

<br/>

<pre>💡 Did you know, you can choose which labels appear on a finding, and whether they show icons or text</pre>

<a href="https://docs.qodo.ai/tips-and-tricks">More tips ↗</a> | <a href="https://app.qodo.ai/configurations?tab=display-preferences">Customize Qodo ↗</a> | <a href="https://docs.qodo.ai">Qodo docs ↗</a>

</details>

<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">
<!-- qodo-daily-tip:end -->


<!-- https://github.com/SigorMatt/agent-room/commit/073f19de6e3ebc5d3138a385ca7651dbb7994827 -->

<a href="https://www.qodo.ai"><img src="https://www.qodo.ai/wp-content/uploads/2025/03/qodo-logo.svg" width="80" alt="Qodo Logo"></a>