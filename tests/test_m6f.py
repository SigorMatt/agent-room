#!/usr/bin/env python3
"""Tests for M6f (docs/design/m6f-hold-head.md): a MERGE-HOLD names its head, and the DECISION that answers it
lets `gate` and `merge --allow-hold 5` pass only while the PR's code is the code the hold showed (B-11).
Run: python3 tests/test_m6f.py

The harness is test_gate.py's: a local bare git repo stands in for GitHub, `gh` is fake_gh_state.py, and room 1
holds the lead's MERGE-HOLDs and the architect's DECISIONs. Everything runs offline.
"""
import os
import re
import shutil
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_gate as T  # noqa: E402  (its own tests run only when it runs as a script)

R, PR = T.R, T.PR
CI = ".github/workflows/ci.yml"
HELD = f"{CI} (`.github/workflows/**`, CI and workflow files)"
RUN = {"id": 1, "name": "ci", "status": "completed", "conclusion": "success", "app": {"slug": "github-actions"}}


def last(r):
    """The gate's verdict line, as printed (test_gate's verdict() drops a FAIL line's head)."""
    lines = [ln for ln in r.stdout.splitlines() if ln.startswith("gate: ")]
    assert lines, T.out(r)
    return lines[-1]


def held_mission():
    """PR #12 with a change to a held path (CI), reviewed and with green checks: mission()'s dict."""
    s = T.mission(extra={CI: "on: push\n"})
    s["covered"], s["scoped"] = s["c2"], 0
    T.gh_cfg(check_runs={s["head"]: [RUN]})
    return s


def push(s, files, msg="feat: change", review=True):
    """A commit on PR #12 and, for code, a scoped cold review covering it; published, checks green. The new head."""
    T.start(base=s["head"])
    code = T.commit(msg, files)
    if review:
        s["scoped"] += 1
        k = s["scoped"]
        T.commit(f"review: cold M3 scoped {k}",
                 {f"reviews/cold/M3/scoped-{k}.md": T.cold_report(k, code, kind="scoped", since=s["covered"])})
        s["covered"] = code
    s["head"] = T.publish()
    T.gh_cfg(check_runs={s["head"]: [RUN]})
    return s["head"]


def hold(n, head, paths=CI):
    """The lead's MERGE-HOLD-N for PATHS, naming HEAD as given: its comment id."""
    return T.say_id("1", "lead", f"MERGE-HOLD-{n}: PR #{PR}, reason 5 (sensitive paths): {paths}, head {head}")


def decide(n):
    return T.say_id("1", "architect", f"DECISION-{n}: merge it")


def answered(n, head):
    """MERGE-HOLD-N naming HEAD, then DECISION-N: their comment ids."""
    return hold(n, head), decide(n)


def allow(n, *command):
    """gate (or COMMAND) with --allow-hold 5 --decision DECISION-N."""
    return T.room(*(command or ("gate", PR)), "--allow-hold", "5", "--decision", f"DECISION-{n}")


def refused(r, text, head):
    """The gate refused at HEAD for reason 5 with TEXT after the held path and the flags."""
    assert r.returncode == 6 and last(r) == f"gate: FAIL hold reasons 5 (head {head[:12]})", T.out(r)
    T.failed(r, "sensitive paths", f"{HELD}; --allow-hold 5 --decision DECISION-")
    T.failed(r, "sensitive paths", text)


# --- the head token, without GitHub

def t_a_hold_names_its_head():  # the head that ends its first line, and only that one (cold M6f R1-1)
    hh, h, old = R.hold_head, "0123456789abcdef0123456789abcdef01234567", "fedcba9876543210fedc"
    text = f"MERGE-HOLD-1: PR #12, reason 5 (sensitive paths): {CI}"
    for tail, want in ((f", head {h[:12]}", h[:12]), (f", head {h}", h), (f" head  {h[:20].upper()} ", h[:20]),
                       (f",head {h[:12]}\r\nmore", h[:12]), (f", Head {h[:12]}\n\nSupersedes MERGE-HOLD-0 (head {old})", h[:12]),
                       (f", head {old}, head {h[:12]}", h[:12]), (f" (head {old} is older), head {h[:12]}", h[:12]), (f", head {h[:12]}.", h[:12]),
                       (f", head {h}. \nNext line.", h)):
        assert hh(text + tail) == want, tail
    assert hh(f"MERGE-HOLD-1: head {h[:12]}") == h[:12]
    for tail in (f", head {h[:11]}", f", head {h}0", f", head {h[:12]}g", f", ahead {h[:12]}", f", head: {h[:12]}",
                 f", head `{h[:12]}`", f", {h[:12]}", f", head {h[:12]}..", f" (head {h[:12]})", f"\nhead {h[:12]}",
                 f", head {h[:12]}.ok", f", head {h[:12]}. ok", f", head {h[:12]},",
                 f", head {h[:12]} (the current one)", f"\n\nThe gate said: post a new hold for head {h[:12]}", ""):
        assert hh(text + tail) is None, tail
    assert R.hold_problems(text, 12, [CI]) == ["a head"]
    assert R.hold_problems(f"{text}, head {h[:12]}", 12, [CI]) == []
    assert R.hold_problems("MERGE-HOLD-1: PR #13", 12, [CI]) == ["PR #12", "reason 5", CI, "a head"]


# --- gate --allow-hold 5 --decision against the gated head

def t_the_verdict_names_the_head():
    s = T.mission()
    r = T.gate()
    assert r.returncode == 0 and last(r) == f"gate: PASS {s['head']}", T.out(r)
    T.start(base=s["head"])
    T.commit("feat: farewell", {"app.py": T.APP2 + "def bye():\n    return 'bye'\n"})
    top = T.publish()
    r = T.gate()
    assert r.returncode == 6 and last(r) == f"gate: FAIL hold reasons none; fix first: coverage (head {top[:12]})", \
        T.out(r)
    s = held_mission()
    r = T.gate()
    assert r.returncode == 6 and last(r) == f"gate: FAIL hold reasons 5 (head {s['head'][:12]})", T.out(r)
    T.set_pr(s["head"], state="closed")  # the PR's problems come before its head is fetched: no head
    r = T.gate()
    assert r.returncode == 6 and last(r) == "gate: FAIL hold reasons none; fix first: PR", T.out(r)
    T.set_pr(s["head"])


def t_a_decision_at_the_holds_own_head():
    s = held_mission()
    h = s["head"]
    hid, did = hold(1, h[:12]), decide(1)
    r = allow(1)
    assert r.returncode == 0 and last(r) == f"gate: PASS {h}", T.out(r)
    assert f"allowed by DECISION-1 (comment #{did}), answering MERGE-HOLD-1 (comment #{hid})" in T.line(r, "sensitive paths")
    answered(2, h)  # all 40 digits
    assert allow(2).returncode == 0
    answered(18, f"{h[:12]}.")  # a sentence's period after it (cold M6f scoped-1 S1-2)
    r = allow(18)
    assert r.returncode == 0 and last(r) == f"gate: PASS {h}", T.out(r)


def t_only_review_records_changed_since():  # the decision's own record push (cold M6e scoped-6 S6-2)
    s = held_mission()
    h1 = s["head"]
    answered(3, h1[:12])
    rows = [("R1-1", "high", "app.py", f"fixed in {s['c2'][:7]}"),
            ("R1-2", "low", "app.py", "dismissed: the caller checks the name (DECISION-3 merges the CI change)")]
    h2 = push(s, dict(T.qodo_archive(2, T.QODO_FINDINGS, s["c2"]), **{
        "reviews/cold/M3/DISPOSITIONS.md": T.cold_dispositions(rows),
        f"reviews/qodo/PR-{PR}/DISPOSITIONS.md": T.qodo_dispositions(T.default_qodo_rows(s), reviewed=s["c2"],
                                                                     fetches="1, 2")}),
              msg="review: qodo fetch 2, DECISION-3's rows", review=False)
    changed = T.g("diff", "--name-only", h1, h2).stdout.split()
    assert len(changed) == 6 and all(R.exempt(p) for p in changed), changed
    r = allow(3)
    assert r.returncode == 0 and last(r) == f"gate: PASS {h2}", T.out(r)


def t_another_path_changed_since():
    s = held_mission()
    h1 = s["head"]
    answered(4, h1[:12])
    h2 = push(s, {"app.py": T.APP2 + "def bye():\n    return 'bye'\n"})  # with its scoped review, a record
    r = allow(4)
    T.passed(r, "coverage")
    refused(r, f"--allow-hold 5 --decision DECISION-4: MERGE-HOLD-4 was posted for head {h1[:12]}; PR #{PR} changed "
               f"since (app.py): post a new hold for head {h2[:12]}", h2)
    # five paths, then how many more; a file under reviews/ that isn't a record counts
    h3 = push(s, dict({f"lib/m{i}.py": "x = 1\n" for i in range(6)}, **{"reviews/cold/M3/notes.md": "notes\n"}))
    T.failed(allow(4), "sensitive paths", f"MERGE-HOLD-4 was posted for head {h1[:12]}; PR #{PR} changed since "
                                          f"(app.py, lib/m0.py, lib/m1.py, lib/m2.py, lib/m3.py and 3 more): "
                                          f"post a new hold for head {h3[:12]}")
    answered(5, h3[:12])
    assert allow(5).returncode == 0


def t_a_head_outside_the_prs_history():
    s = held_mission()
    h1 = s["head"]
    answered(6, h1[:12])
    T.g("commit", "--amend", "-q", "-m", "review: cold round 2, qodo fetch 1, dispositions (reworded)")
    h2 = s["head"] = T.publish()  # a force push: the same code, another history
    T.gh_cfg(check_runs={h2: [RUN]})
    assert h2 != h1 and T.g("diff", "--name-only", h1, h2).stdout == ""
    assert T.g("cat-file", "-t", h1).stdout.strip() == "commit", "the old head is still in the checkout"
    refused(allow(6), f"MERGE-HOLD-6 names head {h1[:12]}, which isn't in PR #{PR}'s history: "
                      f"post a new hold for head {h2[:12]}", h2)
    blob = T.g("rev-parse", f"{h2}:app.py").stdout.strip()
    ref = "abcdefabcdef0123"  # a branch named like a hex head is no commit id (cold M6f R1-3)
    T.g("branch", "-f", ref, h2)
    try:
        for n, named in ((7, "deadbeefdeadbeef"), (8, blob[:12]), (9, ref)):
            answered(n, named)
            refused(allow(n), f"MERGE-HOLD-{n} names head {named}, which isn't in PR #{PR}'s history: "
                              f"post a new hold for head {h2[:12]}", h2)
    finally:
        T.g("branch", "-D", ref)
    answered(10, h2[:12].upper())
    assert allow(10).returncode == 0


def t_a_hold_without_a_head():
    s = held_mission()
    h = s["head"]
    for n, tail in ((11, ""), (12, f", head {h[:11]}"), (13, f", head {h}0"), (14, f", ahead {h[:12]}"),
                    (15, f"\nhead {h[:12]}"), (16, f", head {h[:12]} ok")):  # on a later line, or not ending the first
        T.say_id("1", "lead", f"MERGE-HOLD-{n}: PR #{PR}, reason 5 (sensitive paths): {CI}{tail}")
        decide(n)
        r = allow(n)
        refused(r, f"room 1 has no MERGE-HOLD-{n} for this hold: the lead's doesn't name a head (the form: "
                   f"MERGE-HOLD-<n>: PR #{PR}, reason 5 (sensitive paths): {CI}, head {h[:12]})", h)
    form = re.search(r"\(the form: (.*)\)$", T.line(r, "sensitive paths")).group(1)
    T.say_id("1", "lead", form.replace("<n>", "17"))  # the form, as printed, is a hold that pairs
    decide(17)
    assert allow(17).returncode == 0


def t_b11_an_older_holds_decision_at_a_newer_head():  # cold M6e scoped-5 S5-2, scoped-6 S6-2, S6-3
    s = held_mission()
    h1 = s["head"]
    hold(37, h1[:12])
    h2 = push(s, {CI: "on: [push, pull_request]\n"}, msg="ci: run on pull requests too")  # a held path changes
    h38 = hold(38, h2[:12])
    decide(37)
    refused(allow(37), f"MERGE-HOLD-37 was posted for head {h1[:12]}; PR #{PR} changed since ({CI}): "
                       f"post a new hold for head {h2[:12]}", h2)
    refused(allow(38), f"room 1 has no trusted DECISION-38 from the architect or Matthew after MERGE-HOLD-38 "
                       f"(comment #{h38})", h2)
    decide(38)
    r = allow(38)
    assert r.returncode == 0 and last(r) == f"gate: PASS {h2}", T.out(r)
    assert allow(37).returncode == 6, "DECISION-37 still answers a hold for other code"


def t_only_the_prs_newest_reason5_hold_counts():  # qodo PR #16 finding 1 (cold M6f exp2 b10)
    s = held_mission()
    h1 = s["head"]
    hold(73, h1[:12])
    rows = T.qodo_dispositions(T.default_qodo_rows(s), reviewed=s["c1"]) + "\n"
    h2 = push(s, {f"reviews/qodo/PR-{PR}/DISPOSITIONS.md": rows}, msg="review: rows", review=False)
    hold(74, h2[:12])  # B-10's record-only re-hold: the same code
    assert T.g("diff", h1, h2, "--", CI).stdout == ""
    T.say_id("1", "architect", "DECISION-73: superseded by MERGE-HOLD-74, allows nothing")
    newest = f"MERGE-HOLD-73 is not PR #{PR}'s newest reason-5 hold: MERGE-HOLD-74 came after it; use its DECISION"
    refused(allow(73), newest, h2)
    open(T.CALLS, "w").close()
    r = allow(73, "merge", PR, "--sha", h2)
    refused(r, newest, h2)
    assert T.calls() == [] and T.block()["intent"] == "none", T.out(r)
    decide(74)
    assert allow(74).returncode == 0
    # another PR's hold doesn't count, nor one whose first line doesn't name reason 5 (cold M6f scoped-1 S1-1)
    T.say_id("1", "lead", f"MERGE-HOLD-75: PR #13, reason 5 (sensitive paths): {CI}, head {h2[:12]}\nNot PR #{PR}.")
    T.say_id("1", "lead", f"MERGE-HOLD-76: PR #{PR}, reason 3 (checks fail): ci, head {h2[:12]}")
    T.say_id("1", "lead", f"MERGE-HOLD-77: PR #{PR}, reason 4 (scope), head {h2[:12]}\nReason 5 is DECISION-74's.")
    assert allow(74).returncode == 0
    hold(78, h2[:12])  # a later reason-5 hold does
    refused(allow(74), f"MERGE-HOLD-74 is not PR #{PR}'s newest reason-5 hold: MERGE-HOLD-78 came after it; "
                       f"use its DECISION", h2)
    # the same number again: only the newer hold's decision
    answered(79, h2[:12])
    assert allow(79).returncode == 0
    hold(79, h2[:12])
    refused(allow(79), f"MERGE-HOLD-79 is not PR #{PR}'s newest reason-5 hold: MERGE-HOLD-79 came after it; "
                       f"use its DECISION", h2)
    decide(79)
    assert allow(79).returncode == 0


def t_a_later_hold_for_another_reason():  # cold M6f scoped-1 S1-1 (s1.py reason3_after_merge, reason6_after_pass)
    s = held_mission()
    h1 = s["head"]
    answered(95, h1[:12])
    rows = T.qodo_dispositions(T.default_qodo_rows(s), reviewed=s["c1"]) + "\n<!-- DECISION-95 rows -->\n"
    h2 = push(s, {f"reviews/qodo/PR-{PR}/DISPOSITIONS.md": rows}, msg="review: DECISION-95 rows", review=False)
    T.gh_cfg(merge={"_status": 405, "message": "Pull Request is not mergeable"})
    r = allow(95, "merge", PR, "--sha", h2)  # LEAD.md 5.6 step 6: GitHub says not mergeable
    assert r.returncode == 6 and "not mergeable" in r.stdout and last(r) == f"gate: PASS {h2}", T.out(r)
    T.say_id("1", "lead", f"MERGE-HOLD-96: PR #{PR}, reason 3 (not mergeable: merge commits are off), head {h2[:12]}")
    T.say_id("1", "architect", "DECISION-96: merge commits are allowed now.\nMission: continue.")
    T.gh_reset()
    T.gh_cfg(check_runs={h2: [RUN]})
    T.say_id("1", "lead", f"MERGE-HOLD-97: PR #{PR}, reason 6 (qodo: no first review), head {h2[:12]}.")
    decide(97)
    open(T.CALLS, "w").close()
    r = allow(95, "merge", PR, "--sha", h2)  # the reason-5 decision still allows the held path
    assert r.returncode == 0 and last(r) == f"gate: PASS {h2}", T.out(r)
    assert "allowed by DECISION-95" in T.line(r, "sensitive paths"), T.out(r)
    assert T.calls()[-1] == {"pr": PR, "sha": h2, "merge_method": "merge"}, T.calls()


def t_only_the_first_lines_trailing_head_counts():  # cold M6f R1-1 (exp3 supersedes, exp1 two_heads)
    s = held_mission()
    h1 = s["head"]
    hold(83, h1[:12])
    h2 = push(s, {CI: "on: [push, pull_request]\n"}, msg="ci: run on pull requests too")
    said = T.line(allow(83), "sensitive paths").split("--decision DECISION-83: ", 1)[1]
    assert said.endswith(f"post a new hold for head {h2[:12]}") and h1[:12] in said, said
    T.say_id("1", "lead", f"MERGE-HOLD-84: PR #{PR}, reason 5 (sensitive paths): {CI}, head {h2[:12]}\n"
                          f"Supersedes MERGE-HOLD-83 (head {h1[:12]}): {CI} changed since.")
    T.say_id("1", "architect", "DECISION-83: superseded by MERGE-HOLD-84")
    decide(84)
    r = allow(84)
    assert r.returncode == 0 and last(r) == f"gate: PASS {h2}", T.out(r)
    T.say_id("1", "lead", f"MERGE-HOLD-85: PR #{PR}, reason 5 (sensitive paths): {CI}, head {h2[:12]}\n"
                          f"The gate said: {said}")  # a quoted refusal names two heads
    decide(85)
    assert allow(85).returncode == 0
    answered(86, f"{h1[:12]}, head {h2[:12]}")  # an older head earlier on the first line
    assert allow(86).returncode == 0
    answered(87, f"{h2[:12]} comes next, head {h1[:12]}")  # the first line ends with the older head
    refused(allow(87), f"MERGE-HOLD-87 was posted for head {h1[:12]}; PR #{PR} changed since ({CI}): "
                       f"post a new hold for head {h2[:12]}", h2)


def t_a_ref_named_like_the_head_doesnt_shadow_it():  # cold M6f R1-3 (exp1 tag_and_branch)
    s = held_mission()
    h1 = s["head"]
    h2 = push(s, {CI: "on: [push]\n"}, msg="ci: change")
    T.g("tag", h2[:12], h1)  # named like the current head, at the older code
    T.g("branch", "-f", h1[:12], h2)  # named like the older head, at the current code
    T.g("tag", "-a", "-m", "annotated", "annotated", h2)
    tag = T.g("rev-parse", "annotated").stdout.strip()
    try:
        answered(63, h2[:12])
        r = allow(63)
        assert r.returncode == 0 and last(r) == f"gate: PASS {h2}", T.out(r)
        answered(64, h1[:12])
        refused(allow(64), f"MERGE-HOLD-64 was posted for head {h1[:12]}; PR #{PR} changed since ({CI}): "
                           f"post a new hold for head {h2[:12]}", h2)
        answered(65, tag[:12])  # a tag object's id is no commit's
        refused(allow(65), f"MERGE-HOLD-65 names head {tag[:12]}, which isn't in PR #{PR}'s history: "
                           f"post a new hold for head {h2[:12]}", h2)
    finally:
        T.g("tag", "-d", h2[:12], "annotated")
        T.g("branch", "-D", h1[:12])


def t_a_stale_hold_posted_again_or_edited():
    s = held_mission()
    h1 = s["head"]
    answered(40, h1[:12])
    h2 = push(s, {CI: "on: [push]\n"})
    refused(allow(40), f"MERGE-HOLD-40 was posted for head {h1[:12]}; PR #{PR} changed since ({CI})", h2)
    again = hold(40, h2[:12])  # the same number again: it needs a decision after it
    refused(allow(40), f"no trusted DECISION-40 from the architect or Matthew after MERGE-HOLD-40 (comment #{again})", h2)
    decide(40)
    assert allow(40).returncode == 0
    s = held_mission()
    h1 = s["head"]
    first = hold(41, h1[:12])
    decide(41)
    h2 = push(s, {CI: "on: [push]\n"})
    T.edit_comment(first, f"head {h1[:12]}", f"head {h2[:12]}")  # the decision answered the old head
    refused(allow(41), f"MERGE-HOLD-41 (comment #{first}) edited after DECISION-41: post a new hold", h2)


# --- merge

def t_merge_behaves_like_the_gate():
    s = held_mission()
    h1 = s["head"]
    answered(50, h1[:12])
    h2 = push(s, {CI: "on: [push, workflow_dispatch]\n"})
    T.say_id("1", "lead", f"MERGE-HOLD-51: PR #{PR}, reason 5 (sensitive paths): {CI}")
    decide(51)
    answered(52, h2[:12])
    open(T.CALLS, "w").close()
    r = allow(50, "merge", PR, "--sha", h2)
    refused(r, f"MERGE-HOLD-50 was posted for head {h1[:12]}; PR #{PR} changed since ({CI}): "
               f"post a new hold for head {h2[:12]}", h2)
    assert T.calls() == [] and T.block()["intent"] == "none", T.out(r)
    r = allow(51, "merge", PR, "--sha", h2)
    refused(r, "the lead's doesn't name a head", h2)
    assert T.calls() == [] and T.block()["intent"] == "none", T.out(r)
    r = allow(52, "merge", PR, "--sha", h2)
    assert r.returncode == 0 and last(r) == f"gate: PASS {h2}", T.out(r)
    assert re.search(rf"^merged PR #{PR}: [0-9a-f]{{40}}$", r.stdout, re.M), T.out(r)
    assert T.calls()[-1] == {"pr": PR, "sha": h2, "merge_method": "merge"} and T.block()["pr"] == f"merged:{PR}"


if __name__ == "__main__":
    T.setup()
    for name, fn in list(globals().items()):
        if name.startswith("t_"):
            T.test(name[2:], fn)
    shutil.rmtree(T.tmp, ignore_errors=True)
    print("all passed")
