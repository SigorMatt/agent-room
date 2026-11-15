<h3>Code Review by Qodo</h3>

<code>🐞 Bugs (0)</code>  <code>📘 Rule violations (0)</code>  <code>📜 Skill insights (0)</code>

<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">

<br/>

<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

<details>
<summary>  1.  <s>Survey tests can expose project credentials</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/647d1442e84d81c81392607d6fde3969e949914a"><code>647d144</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>The survey brief no longer runs anything: step 2 now says to find the test command from files and
>not run it, and the &quot;Never&quot; list forbids installing dependencies, building, or running any repo code
>(&quot;Read files only&quot;). ARCHITECT.md&#x27;s survey step runs the test command only later, in the first
>lead&#x27;s session, so the credential-exposure path via the survey subagent is removed. The fix does not
>add the disposable, credential-free environment the prompt recommends, but it removes the risky
>execution entirely, which addresses the finding.
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ briefs/survey.md[R16]</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>briefs/survey.md</i></b> tells the survey subagent to install repository-declared dependencies and run the
>repository&#x27;s test command without first isolating that execution from its credentials. When an
>existing project&#x27;s checkout contains a malicious install hook or test script, that code runs in the
>architect&#x27;s cloud environment, which can contain project secrets and authenticated GitHub access.
></pre>
></details>

<hr/>
</details>


<br/>

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

<details>
<summary>  2.  <s>A failed download can leave a fake room.py that runs</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/647d1442e84d81c81392607d6fde3969e949914a"><code>647d144</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>SKILL.md&#x27;s loop now chains each download with a non-empty check (test -s) and, for room.py, a Python
>ast.parse check, printing &quot;FAILED &lt;file&gt;&quot; and breaking on failure, and says never to go on with a
>failed file. ARCHITECT.md&#x27;s setup loop gets the same treatment, and the watchdog prompt now removes
>a broken room.py (rm -f), prints FAILED room.py, and skips the watchdog run when the second command
>fails. This addresses the finding&#x27;s core concern (unverified download running as room.py, no
>failed-file identification, watchdog running on a fake room.py) with a different implementation than
>the suggested temp-file-and-move approach. The --help check was replaced by an AST parse check.
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ .claude/skills/agent-room/SKILL.md[R37-40]</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
>The skill’s download loop redirects the <b><i>gh api</i></b> fallback into <b><i>$f</i></b> without checking whether it
>succeeds, while the scheduled watchdog prompt invokes <b><i>python3 room.py watchdog</i></b> without first
>verifying the download. When both download methods fail, <b><i>room.py</i></b> can be empty or contain an error
>body that Python treats as a no-op expression, so the watchdog never executes; the loop does not
>identify the failed file, and disabled task notifications leave the missing stall alarm unnoticed.
></pre>
></details>

<hr/>
</details>


<details>
<summary>  3.  <s>Help can delay replacing a silent lead</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/647d1442e84d81c81392607d6fde3969e949914a"><code>647d144</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>room.py join-line --takeover help (line ~3353) was rewritten from &quot;for the lead Matthew starts after
>LEAD-SILENT&quot; to &quot;for a lead Matthew starts once the architect finds the old lead gone: take the
>lease with lease take --takeover&quot;, removing the LEAD-SILENT precondition so both takeover help
>strings now state the same condition.
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ room.py[R1603]</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
>The changed <b><i>lease take --takeover</i></b> help says a replacement may start once the architect finds the
>old lead gone, but the unchanged <b><i>join-line --takeover</i></b> help still requires <b><i>LEAD-SILENT</i></b>. When a
>lead dies while waiting for the owner, the watchdog stays quiet, so an architect following the
>conflicting join-line help may wait for an alarm that will not come.
></pre>
></details>

<hr/>
</details>


<br/>

<img src="https://img.shields.io/badge/Low-634FD1?style=flat-square" height="20px" alt="Informational">

<details>
<summary>  4.  <s>Copied version line breaks the download URLs</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/647d1442e84d81c81392607d6fde3969e949914a"><code>647d144</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>Replaced the grep that printed the whole &#x27;pipeline: &lt;version&gt;&#x27; line with a sed command that extracts
>only the version token, and documented that the output is the bare version, so V is no longer set to
>&#x27;pipeline: v1.0.0&#x27;.
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ .claude/skills/agent-room/SKILL.md[R23]</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
>The architect&#x27;s version lookup runs <b><i>grep &#x27;^pipeline:&#x27;</i></b>, which prints the whole line (`pipeline:
>v1.0.0<b><i>). The next step sets </i></b>V=&lt;version&gt;<b><i> without saying to strip the </i></b>pipeline:` prefix, which
>room.py itself removes with <b><i>^pipeline:[ \t]*(\S+)</i></b>. If the line is used as is, both download URLs
>point at a nonexistent ref and the protocol won&#x27;t load.
></pre>
></details>

<hr/>
</details>



<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">

<!-- qodo-self-review-slot -->


<!-- qodo-context:start -->
<details><summary><strong>Context sources</strong></summary>

<div>&#x2705; Context preparation</div>
<div>&nbsp;&nbsp;Commit messages: summarized; full text retained for this review</div>
<div>Review mode: <code>Auto: 🧠 Deep</code>: Many independent protocol, manual, test, and runtime changes create dense defect risk.</div>
<!-- qodo-context:end -->
</details>

<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">



<!-- qodo-daily-tip:start -->

<details>
<summary><strong>Tip of the day</strong></summary>

<br/>

<pre>💡 Did you know, you can reply &#x27;qodo&#x27; on any finding to push back, ask questions, or dig deeper</pre>

<a href="https://docs.qodo.ai/tips-and-tricks">More tips ↗</a> | <a href="https://app.qodo.ai/configurations?tab=display-preferences">Customize Qodo ↗</a> | <a href="https://docs.qodo.ai">Qodo docs ↗</a>

</details>

<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">
<!-- qodo-daily-tip:end -->


<!-- https://github.com/SigorMatt/agent-room/commit/647d1442e84d81c81392607d6fde3969e949914a -->

<a href="https://www.qodo.ai"><img src="https://www.qodo.ai/wp-content/uploads/2025/03/qodo-logo.svg" width="80" alt="Qodo Logo"></a>