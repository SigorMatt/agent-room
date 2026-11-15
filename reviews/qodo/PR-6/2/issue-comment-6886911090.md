<h3>Code Review by Qodo</h3>

<code>🐞 Bugs (1)</code>  <code>📘 Rule violations (0)</code>  <code>📜 Skill insights (0)</code>

<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">

<br/>

<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

<details>
<summary>  1.  <s>A damaged block restores an old lead</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/a7819374fe298f7392e483186191e470f51bce15"><code>a781937</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>The regex-based STATE_BLOCK/BROKEN_BLOCK parsing is replaced by a strict line-based parser:
>fenced_blocks/locate_block require the agent-room-state block to be the first fenced block, unique,
>with a closing fence, and with only key: value body lines (each key once); otherwise BlockUnreadable
>is raised. A quoted same-info copy now causes an invalid block (two blocks), so pushed_lease walks
>back to the last valid commit instead of trusting the damaged tip. commit path refuses duplicate
>blocks via check_missions/locate_block. Damaged fences are renamed to agent-room-state-damaged
>rather than spanning content, so a later fence can no longer be consumed as the closer. This
>addresses the finding with a different implementation than the suggested regex-based fix.
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ room.py[R553-554]</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>STATE_BLOCK</i></b> can treat a later fence as the missing closing fence, and <b><i>read_block</i></b> accepts the
>first parseable matching block even if it is a quoted copy below the real one. After an outside edit
>damages either fence, an old lease copied into mission notes can become authoritative without a
>warning, allowing a superseded lead to post, close the room, or reuse a counter.
></pre>
></details>

<hr/>
</details>


<details>
<summary>  2.  <s>Recovery can move the project checkout</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/a7819374fe298f7392e483186191e470f51bce15"><code>a781937</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>The commit removes the cwd-based is_stale_state_worktree/project_toplevel logic and replaces it with
>a candidate-directory check. has_marker() inspects the candidate&#x27;s own git dir for the STATE_MARKER
>file that room.py writes only into worktrees/clones it creates, so the project checkout (no marker,
>no state history) is refused regardless of cwd. state_checkout() now resolves the project root from
>--git-common-dir rather than cwd-relative toplevel, and ensure_worktree() computes root before
>moving anything. check_state_dir refuses directories without the marker, and
>t_only_marked_dirs_are_moved tests the project checkout being refused from work, tmp and a builder
>worktree. The approach differs from the suggested Git-metadata inspection but addresses the same
>hazard.
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ room.py[R641-642]</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>is_stale_state_worktree</i></b> identifies the project checkout through the process&#x27;s current directory
>rather than the directory it is about to move. If <b><i>ROOM_STATE_DIR</i></b> names a detached project checkout
>and the command runs from elsewhere, <b><i>ensure_worktree</i></b> can rename that checkout and replace its path
>with a state worktree, disrupting linked builder worktrees.
></pre>
></details>

<hr/>
</details>


<details>
<summary>  3.  <s>Block repair erases mission records</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/a7819374fe298f7392e483186191e470f51bce15"><code>a781937</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>The fix removes the BROKEN_BLOCK span-based replacement in with_block. The new code never deletes
>text through a damaged fence: write_block/locate_block parse the block strictly (only the first
>fenced block with info string agent-room-state counts, closed by a bare fence), and when the block
>is invalid with_block renames every agent-room-state fence to agent-room-state-damaged in place and
>prepends a fresh canonical block under the title. Nothing between fences is removed, matching the
>suggested approach of prepending a valid block and retiring the damaged fence while preserving
>prose. Also the regex-based BROKEN_BLOCK/STATE_BLOCK constants are replaced by the fence-line
>parser.
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ room.py[R882-884]</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>BROKEN_BLOCK</i></b> can span from a damaged opening fence to a later fence in the mission notes, and
><b><i>with_block</i></b> replaces that entire span with a restored block. If an outside edit also removes the
>block&#x27;s closing fence, the next state write can delete intervening mission tables, tasks, and parked
>questions from the pushed file.
></pre>
></details>

<hr/>
</details>


<br/>

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

<details>
<summary>  4.  <s>Preflight can report no admin bypass when it couldn&#x27;t read the ruleset</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/a7819374fe298f7392e483186191e470f51bce15"><code>a781937</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>Added an <b><i>unread</i></b> list in cmd_preflight that records each ruleset id whose detail request returned
>non-200 or a non-dict response. After the bypass loop, it appends &quot;couldn&#x27;t read ruleset &lt;id&gt;, so
>its bypass actors are unknown&quot; to the bypass list, which makes the check print a &quot;!&quot; warning instead
>of &quot;✓ admin bypass: none&quot;. This follows the suggested fix&#x27;s approach (track unreadable rulesets,
>report unknown) though the warning text differs slightly from the suggested format. A regression
>test t_preflight_approving_reviews was also added.
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ room.py[R1240-1243]</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>cmd_preflight</i></b> stores <b><i>{}</i></b> for a failed or non-dict ruleset-detail response without recording that
>the ruleset could not be inspected. When branch rules identify that ruleset, the bypass check finds
>no actors in the empty dictionary and can print <b><i>✓ admin bypass: none</i></b> instead of an unknown
>warning, because its existing error path covers only protection and branch-rules requests.
></pre>
></details>

<hr/>
</details>


<details>
<summary>  5.  <s>One lead can hide messages from another</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/a7819374fe298f7392e483186191e470f51bce15"><code>a781937</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>Cursor files are now keyed per room, role and session (cursor_file uses session_id()), so two lead
>sessions on one machine no longer move each other&#x27;s read cursor; a new test t_two_leads_one_machine
>asserts separate cursor files and independent reads.
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ room.py[R319]</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>unseen</i></b> now distinguishes leads by session, but <b><i>cursor_file</i></b> still stores one cursor per room and
>role. When two lead sessions share a machine, the first lead&#x27;s read advances the second lead&#x27;s
>cursor past architect messages that the second has not seen.
></pre>
></details>

<hr/>
</details>


<details>
<summary>  6.  <s>Recovery strands unpushed state commits</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/a7819374fe298f7392e483186191e470f51bce15"><code>a781937</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>The fix adds save_local_work(), which, before a stale state worktree is moved aside, commits its
>HEAD and uncommitted changes to a durable ref (refs/agent-room/broken-&lt;stamp&gt;) in the project
>repository, falling back to a patch file if that fails. move_aside() now takes save=True from
>ensure_worktree() and reports the saved ref in its notice. This preserves the unpushed commit under
>a durable ref rather than checking and refusing, a different but valid implementation of the
>suggested &quot;preserve HEAD under a durable ref&quot; remediation. Tests
>t_stale_worktree_local_work_is_saved verify the unpushed commit is kept.
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ room.py[R679]</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>ensure_worktree</i></b> moves a stale linked state worktree aside without checking whether it contains
>local changes or unpushed commits. When it prunes and recreates the worktree at the original path,
>the moved copy&#x27;s Git administrative link can point at the replacement, leaving its earlier commit
>without a normal ref or reflog.
></pre>
></details>

<hr/>
</details>


<details><summary><ins><strong>View medium (2)</strong></ins></summary><br/>
<details>
<summary>  7.  <s>A lead inside stale state cannot recover</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/a7819374fe298f7392e483186191e470f51bce15"><code>a781937</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>The commit makes ensure_worktree resolve the project checkout before anything moves (&quot;root =
>state_checkout()  # before anything moves: the current directory may be inside the one moved
>aside&quot;), and uses that stable root for ls_heads(root) and for the later worktree/clone recreation.
>state_checkout() now returns the main worktree via --git-common-dir, never a state clone, so
>recovery Git operations run from a stable location. The stale-worktree check is also reworked to
>recognize candidates by a STATE_MARKER written by room.py (mark(path)), independent of the invoking
>cwd, and save_local_work runs before the move. Together this addresses running recovery from inside
>the directory being replaced, which is the finding&#x27;s premise and requested remediation.
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ room.py[R679]</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>ensure_worktree</i></b> rebuilds a stale state directory while Git commands and checkout discovery still
>depend on the invoking directory. When a lead runs a state command from inside a state worktree
>whose branch was recreated, clone-mode recovery can refuse it and linked-worktree recovery can fail
>partway through after moving it.
></pre>
></details>

<hr/>
</details>


<details>
<summary>  8.  Weakened tests evade the merge hold <code>🐞 Bug</code> <code>≡ Correctness</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
>The M3 gate specification says a merge-hold bullet containing <b><i>deleted</i></b> matches only deleted paths,
>while the default playbook puts deleted and weakened tests in that same bullet. An edit to an
>existing test therefore matches the test globs but does not trigger the sensitive-path hold required
>by the governing design.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[docs/design/m3-reviews-gate.md[109]](https://github.com/SigorMatt/agent-room/pull/6/files#diff-1d80bc747f61196b20f463418d4f5a8ed63e17504c309ba79834aa3278ce332fR109-R109)</code>
>
>```diff
>+6. **Sensitive paths:** the changed paths (`git diff --name-status origin/main...HEAD`) against the globs of the "## Merge-hold list" section of `PLAYBOOK.md` on the state branch. The template has one bullet per area, ``- <label>: `glob`, `glob` ``; every backticked glob in a bullet counts. `*` matches within a path segment, `**` across segments. A bullet whose label contains "deleted" (any case) matches only deleted paths, so adding or editing tests never holds; weakened tests are the cold reviewer's to flag. A match fails with hold reason 5, naming the path and the glob, unless `--allow-hold 5 --decision DECISION-<n>` is given and the room holds a trusted architect comment whose kind is that `DECISION-<n>`. A playbook with no merge-hold section, or one with no globs, fails: the gate never runs without the list.
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>The new specification excludes non-deletions for the template&#x27;s combined test bullet, whereas v1
>includes weakened tests among sensitive changes and requires matching paths to fail the gate.
></pre>
>
> <code>[docs/design/m3-reviews-gate.md\[108-109\]](https://github.com/SigorMatt/agent-room/blob/a7819374fe298f7392e483186191e470f51bce15/docs/design/m3-reviews-gate.md/#L108-L109)</code>
> <code>[templates/playbook/PLAYBOOK.md\[23-31\]](https://github.com/SigorMatt/agent-room/blob/a7819374fe298f7392e483186191e470f51bce15/templates/playbook/PLAYBOOK.md/#L23-L31)</code>
> <code>[docs/design/v1.md\[215-229\]](https://github.com/SigorMatt/agent-room/blob/a7819374fe298f7392e483186191e470f51bce15/docs/design/v1.md/#L215-L229)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>The deleted-only rule exempts modified tests from the default sensitive-path hold, including modifications that weaken them.
>## Fix Focus Areas
>- docs/design/m3-reviews-gate.md[108-109]
>- templates/playbook/PLAYBOOK.md[27-31]
>## Recommended Fix
>Specify a conservative hold for modified tests unless a reliable weakened-test determination is available. Keep the template labels and gate matching rules aligned with that behavior.
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

[Dismiss ↗](https://app.qodo.ai/findings/db26aaf6-31bd-4f77-bfc8-88567e336b51?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/db26aaf6-31bd-4f77-bfc8-88567e336b51)

<hr/>
</details>


</details>
<br/>

<img src="https://img.shields.io/badge/Low-634FD1?style=flat-square" height="20px" alt="Informational">

<details>
<summary>  9.  <s>A failed git diff makes state commit report &#x27;nothing to commit&#x27;</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/a7819374fe298f7392e483186191e470f51bce15"><code>a781937</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>The diff stores the result of <b><i>git diff --cached --quiet</i></b> in <b><i>staged</i></b>, raises StateError with git&#x27;s
>stderr when returncode is neither 0 nor 1, and commits only when returncode == 1. This is exactly
>the suggested fix. A regression test t_failed_git_diff_is_an_error was also added.
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ room.py[R750-753]</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>commit_and_push</i></b> runs <b><i>git diff --cached --quiet</i></b> with <b><i>check=False</i></b> and commits only when it
>returns exactly 1. Any other failure, such as exit 128 from a broken index, is treated as &#x27;no staged
>changes&#x27;. With no unpushed commits, <b><i>state commit</i></b> then prints <b><i>nothing to commit</i></b> and exits 0,
>while the edits stay unpushed in the worktree.
></pre>
></details>

<hr/>
</details>


<details>
<summary>  10.  <s>Preflight --fix failure prints no reason</s> <code>✓ Resolved</code></summary>

<br/>

<p><b>Resolving commit:</b> <a href="https://github.com/SigorMatt/agent-room/commit/a7819374fe298f7392e483186191e470f51bce15"><code>a781937</code></a></p>

> <details>
><summary>Resolution reason</summary>
><br/>
>
><pre>
>The --fix handler now computes why = str(e) or &#x27;the state branch moved; run it again&#x27; and prints it,
>so an empty StateMoved produces the retry hint instead of an empty reason.
></pre>
></details>

<!-- qodo-finding-reference
<code>↗ room.py[R1335-1336]</code>
-->
> <details>
><summary>Description</summary>
><br/>
>
><pre>
>The <b><i>--fix</i></b> handler formats <b><i>{e or &#x27;the state branch moved; run it again&#x27;}</i></b>, but an exception object
>is always truthy, so a bare <b><i>StateMoved()</i></b> (empty message) wins over the fallback. When the
>lead-files push loses a race during <b><i>preflight --fix</i></b>, the output reads `lead-owned files: --fix
>failed: ` with no explanation and no hint to retry.
></pre>
></details>

<hr/>
</details>



<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">

<!-- qodo-self-review-slot -->


<!-- qodo-context:start -->
<details><summary><strong>Context sources</strong></summary>

<div>&#x2705; Web pages:</div>
<div>&nbsp;&nbsp;<a href="https://code.claude.com/docs/en/claude-code-on-the-web?_rsc=1tg4o"><code>🌐 Use Claude Code in the cloud</code></a></div>
<div>&nbsp;&nbsp;<a href="https://github.com/anthropics/claude-code/issues/56879"><code>🌐 [DOCS] [Environment variables] CLAUDE_CODE_SESSION_ID not documented in env-vars reference</code></a></div>
<div>&nbsp;&nbsp;<a href="https://github.com/anthropics/claude-code/issues/65497"><code>🌐 [DOCS] `CLAUDE_CODE_SESSION_ID` env var docs still describe pre-v2.1.163 stdio MCP resume behavior</code></a></div>
<div>&nbsp;&nbsp;<code>+2 more</code></div>
<div>&#x2705; Context preparation</div>
<div>&nbsp;&nbsp;Commit messages: summarized; full text retained for this review</div>
<div>Review mode: <code>Auto: 🧠 Deep</code>: Large stateful CLI with lease, permissions, and many independent paths.</div>
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


<!-- https://github.com/SigorMatt/agent-room/commit/a7819374fe298f7392e483186191e470f51bce15 -->

<a href="https://www.qodo.ai"><img src="https://www.qodo.ai/wp-content/uploads/2025/03/qodo-logo.svg" width="80" alt="Qodo Logo"></a>