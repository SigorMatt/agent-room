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

def t_a_hold_names_its_head():
    hh, h = R.hold_heads, "0123456789abcdef0123456789abcdef01234567"
    assert hh(f"MERGE-HOLD-1: PR #12, reason 5 (sensitive paths): {CI}, head {h[:12]}") == [h[:12]]
    for text, want in ((f"head {h}", h), (f"…, head {h}.", h), (f"(head {h[:12]})", h[:12]),
                       (f"head  {h[:20].upper()};", h[:20]), (f"Head {h[:12]}\n", h[:12])):
        assert hh(text) == [want], text
    for text in (f"head {h[:11]}", f"head {h}0", f"head {h[:12]}g", f"ahead {h[:12]}", f"head: {h[:12]}",
                 f"head `{h[:12]}`", h[:12], "head 0123456789ag"):
        assert hh(text) == [], text
    text = f"MERGE-HOLD-1: PR #12, reason 5 (sensitive paths): {CI}"
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
    ref = "abcdefabcdef0123"  # a branch named like a hex head resolves, but not to a commit of that name
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
    for n, tail in ((11, ""), (12, f", head {h[:11]}"), (13, f", head {h}0"), (14, f", ahead {h[:12]}")):
        T.say_id("1", "lead", f"MERGE-HOLD-{n}: PR #{PR}, reason 5 (sensitive paths): {CI}{tail}")
        decide(n)
        r = allow(n)
        refused(r, f"room 1 has no MERGE-HOLD-{n} for this hold: the lead's doesn't name a head (the form: "
                   f"MERGE-HOLD-<n>: PR #{PR}, reason 5 (sensitive paths): {CI}, head {h[:12]})", h)
    form = re.search(r"\(the form: (.*)\)$", T.line(r, "sensitive paths")).group(1)
    T.say_id("1", "lead", form.replace("<n>", "15"))  # the form, as printed, is a hold that pairs
    decide(15)
    assert allow(15).returncode == 0


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
