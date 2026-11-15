<h3>Code Review by Qodo</h3>

<code>🐞 Bugs (4)</code>  <code>📘 Rule violations (0)</code>  <code>📜 Skill insights (0)</code>

<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">

<br/>

<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

<details>
<summary>  1.  The gate passes checks from the wrong app <code>🐞 Bug</code> <code>≡ Correctness</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>required_contexts()</i></b> discards the <b><i>app_id</i></b> attached to required checks, and <b><i>check_checks()</i></b>
>matches results by context name alone. When a different app reports a successful check with that
>name on HEAD, the gate can pass even though the configured app has not reported its required check.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[room.py[R2200-2201]](https://github.com/SigorMatt/agent-room/pull/7/files#diff-36e706accba1fe5812fd1526e9931f792f8e314ada3f00e0e24e85cd44fb2433R2200-R2201)</code>
>
>```diff
>+        req |= set(rsc.get("contexts") or [])
>+        req |= {c["context"] for c in rsc.get("checks") or [] if c.get("context")}
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>The branch-protection API documents <b><i>checks[].app_id</i></b> as the app that must provide the check. The
>new gate retains only <b><i>context</i></b>, then computes missing requirements from reported names; neither
>step compares app IDs.
></pre>
>
> <code>[room.py\[2194-2210\]](https://github.com/SigorMatt/agent-room/blob/624dfffd335be6e2d94b08ff39d8af1b196b6350/room.py/#L2194-L2210)</code>
> <code>[room.py\[2238-2255\]](https://github.com/SigorMatt/agent-room/blob/624dfffd335be6e2d94b08ff39d8af1b196b6350/room.py/#L2238-L2255)</code>
> <code>[room.py\[2277-2287\]](https://github.com/SigorMatt/agent-room/blob/624dfffd335be6e2d94b08ff39d8af1b196b6350/room.py/#L2277-L2287)</code>
> <code>🌐 [The `checks` entries include an `app_id` specifying which GitHub App must provide a required check.](https://docs.github.com/en/rest/branches/branch-protection)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>Required check configurations can specify a GitHub App, but the gate drops that identity and accepts a same-named result from another app.
>## Fix Focus Areas
>- room.py[2194-2212]
>- room.py[2238-2255]
>- tests/test_gate.py[1079-1140]
>## Recommended Fix
>Preserve each required check's app ID and compare it with the reporting check run's app ID when evaluating required checks. Do not let a same-named result from another app satisfy an app-specific requirement; add a regression test for that case.
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

[Dismiss ↗](https://app.qodo.ai/findings/5c879338-59e4-4678-8daf-290e3cf73f0d?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/5c879338-59e4-4678-8daf-290e3cf73f0d)

<hr/>
</details>


<br/>

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

<details>
<summary>  2.  Qodo findings can have two dispositions <code>🐞 Bug</code> <code>≡ Correctness</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>check_dispositions()</i></b> adds each Qodo title to <b><i>seen</i></b> without rejecting a title already in the set.
>When a dispositions table repeats a finding, both rows can pass validation and the gate reports
>every finding decided despite the conflicting record.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[room.py[R2143-2147]](https://github.com/SigorMatt/agent-room/pull/7/files#diff-36e706accba1fe5812fd1526e9931f792f8e314ada3f00e0e24e85cd44fb2433R2143-R2147)</code>
>
>```diff
>+            key = title_key(row["finding"])
>+            if not key and not row["disposition"].strip():
>+                continue
>+            seen.add(key)
>+            n_qodo += 1
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>The Qodo loop only adds keys to <b><i>seen</i></b>, and the subsequent completeness check tests membership
>rather than uniqueness. The cold-dispositions loop explicitly rejects duplicate IDs, while the
>review procedure requires exactly one disposition per finding.
></pre>
>
> <code>[room.py\[2140-2159\]](https://github.com/SigorMatt/agent-room/blob/624dfffd335be6e2d94b08ff39d8af1b196b6350/room.py/#L2140-L2159)</code>
> <code>[room.py\[2106-2115\]](https://github.com/SigorMatt/agent-room/blob/624dfffd335be6e2d94b08ff39d8af1b196b6350/room.py/#L2106-L2115)</code>
> <code>[docs/design/v1.md\[139-151\]](https://github.com/SigorMatt/agent-room/blob/624dfffd335be6e2d94b08ff39d8af1b196b6350/docs/design/v1.md/#L139-L151)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>The Qodo dispositions check accepts multiple rows for one finding, so a finding can have conflicting recorded dispositions.
>## Fix Focus Areas
>- room.py[2140-2153]
>- tests/test_gate.py[1-1459]
>## Recommended Fix
>Before adding a normalized finding title to `seen`, report a disposition error if it is already present. Add a test with two otherwise valid rows for the same archived Qodo finding and assert that the gate fails.
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

[Dismiss ↗](https://app.qodo.ai/findings/61970255-b735-4379-b46c-00130509ed8c?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/61970255-b735-4379-b46c-00130509ed8c)

<hr/>
</details>


<details>
<summary>  3.  An edited hold releases paths nobody approved <code>🐞 Bug</code> <code>⛨ Security</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>check_sensitive</i></b> reads the lead&#x27;s <b><i>MERGE-HOLD-&lt;n&gt;</i></b> text as it stands when the gate runs. It then
>accepts any trusted <b><i>DECISION-&lt;n&gt;</i></b> whose comment id is larger than the hold&#x27;s, but editing a GitHub
>comment keeps its id and <b><i>parse()</i></b> never reads <b><i>updated_at</i></b>. So if the lead edits an answered hold
>to add a newly matched path, which is what the gate&#x27;s own &quot;doesn&#x27;t name X (the form: …)&quot; message
>invites, the old decision passes for a path Matthew never saw. <b><i>RoomLog.answers</i></b> has the same gap
>for top-severity owner decisions: an <b><i>ESCALATION-&lt;n&gt;</i></b> edited after the decision to name another
>finding makes that decision cover it.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[room.py[R2408-2411]](https://github.com/SigorMatt/agent-room/pull/7/files#diff-36e706accba1fe5812fd1526e9931f792f8e314ada3f00e0e24e85cd44fb2433R2408-R2411)</code>
>
>```diff
>+    holds = room.holds(f"MERGE-HOLD-{n}")
>+    lacking = [hold_problems(m["text"], a.pr, paths) for m in holds]
>+    hold = holds[lacking.index([])] if [] in lacking else None
>+    decision = next((d for d in room.decisions(a.decision) if hold and d["id"] > hold["id"]), None)
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>Hold and decision are compared only by comment <b><i>id</i></b> (lines 2411 and 2341), and the hold&#x27;s paths come
>from its current text (<b><i>hold_problems(m[&quot;text&quot;], …)</i></b>). The M2 <b><i>parse()</i></b> keeps <b><i>id</i></b>, <b><i>created_at</i></b> and
><b><i>text</i></b> but drops <b><i>updated_at</i></b>, so the gate cannot tell when a hold was edited. GitHub comment edits
>change the body and keep the id. The comment at lines 2418-2420 says showing the form is safe
>because a decision must still come after a new hold, but an edit is not a new hold.
></pre>
>
> <code>[room.py\[2405-2423\]](https://github.com/SigorMatt/agent-room/blob/624dfffd335be6e2d94b08ff39d8af1b196b6350/room.py/#L2405-L2423)</code>
> <code>[room.py\[2324-2341\]](https://github.com/SigorMatt/agent-room/blob/624dfffd335be6e2d94b08ff39d8af1b196b6350/room.py/#L2324-L2341)</code>
> <code>[room.py\[203-213\]](https://github.com/SigorMatt/agent-room/blob/624dfffd335be6e2d94b08ff39d8af1b196b6350/room.py/#L203-L213)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>The gate links a DECISION to the lead's MERGE-HOLD/ESCALATION only by comparing comment ids. Edited comments keep their id, so an edit made after the decision changes what the decision appears to approve.
>
>## Fix Focus Areas
>- room.py[203-213]
>- room.py[2324-2341]
>- room.py[2405-2423]
>
>## Recommended Fix
>Have `parse()` also return `updated_at` (falling back to `created_at`). In `check_sensitive`, accept a decision only if the hold's `updated_at` is no later than the decision's `created_at`. In `RoomLog.answers`, accept only asks whose `updated_at` is earlier than the decision's `created_at`. When a hold was edited after its decision, say so in the failure and ask for a new hold and decision. Add a regression test where the fake gh returns an edited hold.
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

[Dismiss ↗](https://app.qodo.ai/findings/c32315dd-5b03-47a5-bf4d-d13f46f1ba7d?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/c32315dd-5b03-47a5-bf4d-d13f46f1ba7d)

<hr/>
</details>


<br/>

<img src="https://img.shields.io/badge/Low-634FD1?style=flat-square" height="20px" alt="Informational">

<details>
<summary>  4.  An unused room lookup is left behind <code>🐞 Bug</code> <code>⚙ Maintainability</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>RoomLog.decision(kind)</i></b> returns the first trusted decision of a kind, but nothing in room.py calls
>it: <b><i>check_sensitive</i></b> and <b><i>answers</i></b> both use <b><i>decisions()</i></b> with their own ordering rules. A later
>caller could reach for <b><i>decision()</i></b> and get a DECISION without the hold and escalation ordering that
>R2-1 and R2-2 added.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[room.py[R2321-2322]](https://github.com/SigorMatt/agent-room/pull/7/files#diff-36e706accba1fe5812fd1526e9931f792f8e314ada3f00e0e24e85cd44fb2433R2321-R2322)</code>
>
>```diff
>+    def decision(self, kind):
>+        return next(iter(self.decisions(kind)), None)
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>A search of room.py finds no <b><i>.decision(</i></b> call. The only lookups of decisions go through
><b><i>decisions()</i></b> together with the id-ordering checks.
></pre>
>
> <code>[room.py\[2317-2345\]](https://github.com/SigorMatt/agent-room/blob/624dfffd335be6e2d94b08ff39d8af1b196b6350/room.py/#L2317-L2345)</code>
> <code>[room.py\[2405-2415\]](https://github.com/SigorMatt/agent-room/blob/624dfffd335be6e2d94b08ff39d8af1b196b6350/room.py/#L2405-L2415)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>`RoomLog.decision` is dead code that skips the ordering rules the gate relies on.
>
>## Fix Focus Areas
>- room.py[2321-2322]
>
>## Recommended Fix
>Remove the method. If a test uses it, switch the test to `decisions()`.
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

[Dismiss ↗](https://app.qodo.ai/findings/12402164-366f-4323-a40b-dd5db6782c59?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/12402164-366f-4323-a40b-dd5db6782c59)

<hr/>
</details>



<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">

<!-- qodo-self-review-slot -->


<!-- qodo-context:start -->
<details><summary><strong>Context sources</strong></summary>

<div>&#x2705; Web pages:</div>
<div>&nbsp;&nbsp;<a href="https://docs.github.com/en/rest/commits/statuses"><code>🌐 REST API endpoints for commit statuses</code></a></div>
<div>&nbsp;&nbsp;<a href="https://docs.github.com/enterprise/2.14/developer/v3/repos/statuses/"><code>🌐 Statuses | GitHub Developer Guide</code></a></div>
<div>&nbsp;&nbsp;<a href="https://www.postman.com/api-evangelist/api-specification-toolbox/request/9ebizzy/get-the-combined-status-for-a-specific-reference"><code>🌐 Get the combined status for a specific reference | API Specification Toolbox | Postman API Network</code></a></div>
<div>&nbsp;&nbsp;<code>+9 more</code></div>
<div>&#x2705; Context preparation</div>
<div>&nbsp;&nbsp;Commit messages: summarized; full text retained for this review</div>
<div>Review mode: <code>Auto: 🧠 Deep</code>: Large gate/merge logic spans many independent paths and contracts.</div>
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


<!-- https://github.com/SigorMatt/agent-room/commit/624dfffd335be6e2d94b08ff39d8af1b196b6350 -->

<a href="https://www.qodo.ai"><img src="https://www.qodo.ai/wp-content/uploads/2025/03/qodo-logo.svg" width="80" alt="Qodo Logo"></a>