#!/usr/bin/env python3
"""Tests for room.py gate and merge, and the review-record parsing behind them. Run: python3 tests/test_gate.py

The project repo is a local bare git repo standing in for GitHub: main, the mission branches and
agent-room/state. `gh` is fake_gh_state.py, which answers PR objects, check runs, statuses, branch
protection and the merge endpoint, and passes room comments on to fake_gh.py.
"""
import importlib.util
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ROOM = os.path.join(ROOT, "room.py")
DOC = os.path.join(ROOT, "docs", "QODO-REVIEW.md")
TEMPLATES = os.path.join(ROOT, "templates", "playbook")
REAL_REVIEW = os.path.join(ROOT, "reviews", "qodo", "PR-5", "3", "issue-comment-6884442048.md")
REAL_DISPOSITIONS = os.path.join(ROOT, "reviews", "qodo", "PR-5", "DISPOSITIONS.md")
tmp = tempfile.mkdtemp(prefix="room-gate-")
BIN = os.path.join(tmp, "bin")
HOME = os.path.join(tmp, "home")
GH_CFG = os.path.join(tmp, "gh-state.json")
CALLS = GH_CFG + ".calls"
STATE_DIR = os.path.join(tmp, "state")
for d in (BIN, HOME):
    os.makedirs(d)
with open(os.path.join(BIN, "gh"), "w") as f:
    f.write(f'#!/bin/sh\nexec "{sys.executable}" "{os.path.join(HERE, "fake_gh_state.py")}" "$@"\n')
os.chmod(os.path.join(BIN, "gh"), 0o755)

ENV = {k: v for k, v in os.environ.items()
       if not k.startswith(("ROOM_", "GIT_", "QODO_", "CLAUDE_CODE_SESSION", "FAKE_GH"))}
ENV.update(PATH=BIN + os.pathsep + os.environ["PATH"], HOME=HOME, XDG_CONFIG_HOME=os.path.join(HOME, ".config"),
           GIT_CONFIG_NOSYSTEM="1", FAKE_GH_DB=os.path.join(tmp, "db.json"), FAKE_GH_STATE=GH_CFG,
           ROOM_REPO="SigorMatt/pet", ROOM_STATE=os.path.join(tmp, "cursors"), ROOM_STATE_DIR=STATE_DIR,
           ROOM_SESSION="L1", QODO_REVIEW="on")
GIT_ENV = dict(ENV, GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="test@example.com",
               GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="test@example.com")

PET = os.path.join(tmp, "git", "SigorMatt", "pet.git")  # /git/OWNER/NAME, like the proxy's URLs
CHECKOUT = os.path.join(tmp, "work", "pet")
BRANCH = "mission/M3-gate"
PR = "12"

spec = importlib.util.spec_from_file_location("room_under_test", ROOM)
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


def g(*args, cwd=CHECKOUT, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, env=GIT_ENV, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise AssertionError(f"git {args} failed: {r.stderr}")
    return r


def room(*args, check=False, stdin=None, **env):
    e = dict(ENV)
    for k, v in env.items():
        if v is None:
            e.pop(k, None)
        else:
            e[k] = v
    r = subprocess.run([sys.executable, ROOM, *args], env=e, cwd=CHECKOUT, input=stdin, capture_output=True,
                       text=True, timeout=120)
    if check and r.returncode != 0:
        raise AssertionError(f"{args} exited {r.returncode}:\n{r.stdout}\n{r.stderr}")
    return r


def out(r):
    return f"exit {r.returncode}\n{r.stdout}\n{r.stderr}"


def line(r, name):
    """The gate's line for check NAME."""
    for ln in r.stdout.splitlines():
        if re.match(rf"[✓✗…] {re.escape(name)}:", ln):
            return ln
    raise AssertionError(f"no line for {name!r}:\n{out(r)}")


def passed(r, name):
    assert line(r, name).startswith("✓ "), out(r)


def failed(r, name, *needles):
    ln = line(r, name)
    assert ln.startswith("✗ "), out(r)
    for n in needles:
        assert n in ln, f"{n!r} not in: {ln}\n{out(r)}"


def verdict(r):
    lines = [ln for ln in r.stdout.splitlines() if ln.startswith("gate: ")]
    assert lines, out(r)
    return lines[-1]


def test(name, fn):
    fn()
    print(f"ok  {name}")


# --- the fake GitHub's answers

CFG = {}


def save():
    with open(GH_CFG, "w") as f:
        json.dump(CFG, f)


def gh_cfg(**kw):
    CFG.update(kw)
    save()


def gh_reset():
    pulls = CFG.get("pulls")
    CFG.clear()
    if pulls:
        CFG["pulls"] = pulls
    save()


def set_pr(sha, ref=BRANCH, state="open", base="main", repo="SigorMatt/pet", merged=False):
    gh_cfg(pulls={PR: {"number": int(PR), "state": state, "merged": merged, "base": {"ref": base},
                       "head": {"ref": ref, "sha": sha, "repo": {"full_name": repo}}}})


def calls():
    try:
        with open(CALLS) as f:
            return [json.loads(x) for x in f if x.strip()]
    except FileNotFoundError:
        return []


def block():
    text = g("--git-dir", PET, "show", "agent-room/state:docs/playbook/MISSIONS.md").stdout
    body = text.split("```agent-room-state\n", 1)[1].split("```", 1)[0]
    return dict(ln.split(": ", 1) if ": " in ln else (ln.rstrip(":"), "") for ln in body.splitlines())


def edit_state(name, fn):
    room("state", "sync", check=True)
    path = os.path.join(STATE_DIR, "docs", "playbook", name)
    with open(path) as f:
        text = f.read()
    with open(path, "w") as f:
        f.write(fn(text))
    room("state", "commit", "-m", f"test: edit {name}", check=True)
    return text


def post_raw(body, login="SigorMatt"):
    subprocess.run([os.path.join(BIN, "gh"), "api", "-X", "POST", "repos/SigorMatt/pet/issues/1/comments",
                    "--input", "-"], env=dict(ENV, FAKE_GH_LOGIN=login), input=json.dumps({"body": body}),
                   capture_output=True, text=True, check=True)


# --- the mission branch and its review records

APP1 = "def greet(name):\n    return 'hi ' + name\n"
APP2 = "def greet(name):\n    return 'hi ' + (name or 'there')\n"
GREY = '<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">'
QODO_FINDINGS = [("Action required", "Crash when the name is missing", True),
                 ("Informational", "Greeting text is hard-coded", False)]


def head():
    return g("rev-parse", "HEAD").stdout.strip()


def start(base="origin/main", branch=BRANCH):
    g("checkout", "-q", "-B", branch, base)


def commit(msg, files):
    for path, text in files.items():
        if text is None:
            g("rm", "-q", path)
            continue
        full = os.path.join(CHECKOUT, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(text)
    g("add", "-A")
    g("commit", "-q", "-m", msg)
    return head()


def publish(branch=BRANCH, **pr):
    g("push", "-q", "-f", "origin", f"HEAD:refs/heads/{branch}")
    sha = head()
    set_pr(sha, ref=branch, **pr)
    return sha


def cold_report(r, covers, findings=(), kind="round", since=None):
    lines = [f"# Cold review M3 {kind} {r}", f"covers: {covers}", f"base: {'b' * 40}", "spec: 1234abc"]
    if since:
        lines.append(f"since: {since}")
    lines += ["", "## Findings", "", "| ID | severity | file:line | finding | failure scenario |",
              "| --- | --- | --- | --- | --- |"]
    lines += [f"| {fid} | {sev} | {where} | a finding | it breaks |" for fid, sev, where in findings]
    if not findings:
        lines += ["", "none"]
    lines += ["", "## Criteria", "", "| criterion | met | evidence |", "| --- | --- | --- |", "| P1-1 | yes | test_greet |",
              "", "## Scope", "", "Inside the spec."]
    return "\n".join(lines) + "\n"


def cold_dispositions(rows):
    lines = ["# Cold dispositions M3", "", "| ID | severity | file | finding | disposition | evidence |",
             "| --- | --- | --- | --- | --- | --- |"]
    lines += [f"| {fid} | {sev} | {path} | a finding | {disp} | test_greet |" for fid, sev, path, disp in rows]
    return "\n".join(lines) + "\n"


def qodo_comment(findings, reviewed):
    open_ = sum(1 for _, _, resolved in findings if not resolved)
    lines = ["<h3>Code Review by Qodo</h3>", "", f"<code>🐞 Bugs ({open_})</code>  <code>📘 Rule violations (0)</code>",
             "", GREY, "", "<br/>", ""]
    last = None
    for i, (sev, title, resolved) in enumerate(findings, 1):
        if sev != last:
            lines += [f'<img src="https://img.shields.io/badge/X-634FD1?style=flat-square" height="20px" alt="{sev}">', ""]
            last = sev
        shown = f"<s>{title}</s> <code>✓ Resolved</code>" if resolved else f"{title} <code>🐞 Bug</code> <code>≡ Correctness</code>"
        lines += ["<details>", f"<summary>  {i}.  {shown}</summary>", "", "<br/>", "", "><summary>Description</summary>",
                  "><pre>", ">It breaks.", "></pre>", "</details>", ""]
    lines += [GREY, "", f"<!-- https://github.com/SigorMatt/pet/commit/{reviewed} -->", ""]
    return "\n".join(lines)


def qodo_archive(k, findings, reviewed, cid=7001):
    base = f"reviews/qodo/PR-{PR}/{k}"
    files = {}
    for i, body in ((cid - 1, "<h3>PR Summary by Qodo</h3>\n\nGreets people.\n"), (cid, qodo_comment(findings, reviewed))):
        files[f"{base}/issue-comment-{i}.md"] = body
        files[f"{base}/issue-comment-{i}.json"] = json.dumps({"id": i, "user": {"login": "qodo-code-review[bot]"},
                                                              "body": body}, indent=2) + "\n"
    return files


def qodo_dispositions(rows, qodo="on", reviewed="", fetches="1"):
    lines = [f"qodo: {qodo}", f"fetches: {fetches}", f"reviewed: {reviewed}", "",
             "| # | severity | finding | tags | file | disposition | Qodo now | cold caught |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    lines += [f"| {n} | {sev} | {title} | 🐞 Bug | {path} | {disp} | open | no |" for n, sev, title, path, disp in rows]
    return "\n".join(lines) + "\n"


def default_cold_rows(s):
    return [("R1-1", "high", "app.py", f"fixed in {s['c2'][:7]}"),
            ("R1-2", "low", "app.py", "dismissed: the caller checks the name (test_greet)")]


def default_qodo_rows(s):
    return [("1", "Action required", "Crash when the name is missing", "app.py", f"fixed in {s['c2'][:7]}"),
            ("2", "Informational", "Greeting text is hard-coded", "app.py", "dismissed: the playbook fixes the text")]


def mission(extra=None, findings1=None, findings2=(), cold_rows=default_cold_rows, qodo_findings=None,
            qodo_rows=default_qodo_rows, qodo="on", qodo_file=True, branch=BRANCH):
    """A mission branch: code (C1), cold round 1 on C1, a fix (C2), cold round 2 on C2, Qodo's fetch 1 on C2
    and both dispositions tables, committed after C2 (a record-only commit). Published as PR #12."""
    start(branch=branch)
    s = {"c1": commit("feat: greet", dict({"app.py": APP1}, **(extra or {})))}
    findings1 = [("R1-1", "high", "app.py:2"), ("R1-2", "low", "app.py:1")] if findings1 is None else findings1
    commit("review: cold M3 round 1", {"reviews/cold/M3/round-1.md": cold_report(1, s["c1"], findings1)})
    s["c2"] = commit("fix: greet without a name (R1-1)", {"app.py": APP2})
    files = {"reviews/cold/M3/round-2.md": cold_report(2, s["c2"], findings2),
             "reviews/cold/M3/DISPOSITIONS.md": cold_dispositions(cold_rows(s))}
    if qodo == "on":
        files.update(qodo_archive(1, QODO_FINDINGS if qodo_findings is None else qodo_findings, s["c2"]))
    if qodo_file:
        files[f"reviews/qodo/PR-{PR}/DISPOSITIONS.md"] = qodo_dispositions(
            qodo_rows(s) if qodo == "on" else [], qodo=qodo, reviewed=s["c2"] if qodo == "on" else "")
    commit("review: cold round 2, qodo fetch 1, dispositions", files)
    s["head"] = publish(branch)
    return s


def gate(*args, **env):
    return room("gate", PR, *args, **env)


def setup():
    g("init", "-q", "--bare", "--initial-branch=main", PET, cwd=tmp)
    g("clone", "-q", PET, CHECKOUT, cwd=tmp)
    room("state", "init", check=True, ROOM_SESSION="arch")
    room("state", "init-lead", check=True)
    room("lease", "take", check=True)
    assert "room 1 in SigorMatt/pet" in room("new", "Phase 1", check=True).stdout
    edit_state("PLAYBOOK.md", lambda t: re.sub(r"^room: 0$", "room: 1", t, count=1, flags=re.M))
    edit_state("LEDGER.md", lambda t: t + "| L-1 | cold M3 R1-3 | a finding | later mission | M4 | open |\n"
                                          "| L-2 | qodo PR #12 #3 | a finding | next phase | phase 2 backlog | open |\n")
    g("fetch", "-q", "origin")
    g("checkout", "-q", "-B", "main", "origin/main")
    commit("app, lib and tests", {"app.py": "def greet(name):\n    return name\n", "lib/util.py": "X = 1\n",
                                  "tests/test_old.py": "def test_greet():\n    pass\n",
                                  "lib/tests/test_x.py": "def test_x():\n    pass\n"})
    g("push", "-q", "origin", "main")
    gh_reset()


# --- parsing, without GitHub

def t_doc_extraction():
    doc = open(DOC, encoding="utf-8").read()
    for marker in ("<!-- BEGIN qodo_review.py -->", "<!-- END qodo_review.py -->"):
        assert len(re.findall(rf"^{re.escape(marker)}$", doc, re.M)) == 1, marker
    m = re.search(r"^python3 -c '(.*)' QODO-REVIEW\.md \S+$", doc, re.M)
    assert m, "the extraction command is gone from QODO-REVIEW.md"
    tool = os.path.join(tmp, "qodo_review.py")
    subprocess.run([sys.executable, "-c", m.group(1), DOC, tool], check=True)
    py_compile.compile(tool, cfile=os.path.join(tmp, "qodo_review.pyc"), doraise=True)
    r = subprocess.run([sys.executable, tool, "--replay", os.path.dirname(REAL_REVIEW)], capture_output=True, text=True)
    assert r.returncode == 2 and "8c9c413a98cbac3dc5dcfdc04a29ae1b470916f5" in r.stdout, out(r)


def t_copied_parsing_matches_the_tool():
    spec = importlib.util.spec_from_file_location("qodo_review", os.path.join(tmp, "qodo_review.py"))
    q = importlib.util.module_from_spec(spec)
    sys.modules["qodo_review"] = q  # its dataclasses look their module up
    spec.loader.exec_module(q)
    for name in ("_HEADING", "_FINDING", "_SEVERITY", "_REVIEWED", "_RESOLVED_MARK"):
        assert getattr(R, name).pattern == getattr(q, name).pattern, name
    for title in ("<s>Fix the <code>x</code> bug</s> <code>✓ Resolved</code>", "A &amp; B ~~struck~~", "a\\_b  c",
                  "Resolved title that is open", "<b>Bold</b>   spaced"):
        assert R.plain(title) == q.plain(title), title
    text = open(REAL_REVIEW, encoding="utf-8").read()
    mine, theirs = R.qodo_findings(text), q.findings(text)
    assert [(f["number"], f["title"], f["severity"]) for f in mine] == [(f.number, f.title, f.severity) for f in theirs]
    assert R.is_code_review(text) and q.is_code_review("issue-comment", {"body": text})
    summary = open(REAL_REVIEW.replace("6884442048", "6884435207"), encoding="utf-8").read()
    assert not R.is_code_review(summary) and not q.is_code_review("issue-comment", {"body": summary})
    assert R._REVIEWED.findall(text)[-1] == q.reviewed_commit(text) == "8c9c413a98cbac3dc5dcfdc04a29ae1b470916f5"


def t_real_archive_and_dispositions():
    found = R.qodo_findings(open(REAL_REVIEW, encoding="utf-8").read())
    assert len(found) == 5 and found[0]["severity"] == "Action required" and found[4]["severity"] == "Informational"
    assert found[0]["title"] == "Approved design says builders push, build state says they never do"
    rows = R.find_table(open(REAL_DISPOSITIONS, encoding="utf-8").read(), ("#", "finding", "disposition"),
                        ("severity", "file"))
    assert {R.title_key(r["finding"]) for r in rows} == {f["key"] for f in found}
    assert R.parse_disposition(rows[0]["disposition"])[0] == "fixed" and rows[0]["file"] == "docs/design/v1.md"


def t_exempt_patterns():
    for p in ("reviews/cold/M3/round-1.md", "reviews/cold/M3/round-2.md", "reviews/cold/M12/round-3.md",
              "reviews/cold/M3/scoped-1.md", "reviews/cold/M3/scoped-14.md", "reviews/cold/M3/DISPOSITIONS.md",
              "reviews/qodo/PR-12/DISPOSITIONS.md", "reviews/qodo/PR-12/1/issue-comment-6884442048.md",
              "reviews/qodo/PR-12/10/issue-comment-6884442048.json", "reviews/qodo/PR-12/2/review-5907229379.json",
              "reviews/qodo/PR-12/3/review-comment-4575709790.md"):
        assert R.exempt(p), p
    for p in ("reviews/cold/M3/notes.md", "reviews/cold/M3/round-1.md.bak", "reviews/cold/round-1.md",
              "reviews/cold/M3/sub/round-1.md", "reviews/cold/MX/round-1.md", "reviews/cold/M3/DISPOSITIONS.MD",
              "reviews/cold/M3/round-.md", "reviews/qodo/PR-12/1/helper.py", "reviews/qodo/PR-12/1/issue-comment-x.md",
              "reviews/qodo/PR-12/1/issue-comment-1.txt", "reviews/qodo/PR-12/issue-comment-1.md",
              "reviews/qodo/PR-x/DISPOSITIONS.md", "reviews/run.py", "xreviews/cold/M3/round-1.md",
              "src/reviews/cold/M3/round-1.md", "reviews/cold/M3/round-1.md/x.py"):
        assert not R.exempt(p), p
    committed = g("ls-files", "reviews", cwd=ROOT).stdout.split()
    assert committed and all(R.exempt(p) for p in committed), [p for p in committed if not R.exempt(p)]


def t_disposition_grammar():
    for cell, form in (("fixed in 6e1dbec", "fixed"), ("fixed in " + "a" * 40, "fixed"), ("fixed in `6e1dbec`", "fixed"),
                       ("dismissed: the test covers it", "dismissed"), ("deferred: L-3 to M4", "deferred"),
                       ("deferred: L-12 to phase 2 backlog", "deferred"),
                       ("owner decision: keep the text, Matthew (DECISION-4)", "owner"),
                       ("owner decision: pending (ESCALATION-5)", "pending")):
        assert R.parse_disposition(cell)[0] == form, cell
    for cell in ("", "fixed", "fixed in 6e1db", "fixed in " + "a" * 41, "fixed in xyz1234", "fixed in 6e1dbec and 8c9c413",
                 "dismissed:", "dismissed:  ", "deferred: L-3", "deferred: L-3 to later", "deferred: B-1 to M3",
                 "deferred: L-3 to phase two backlog", "owner decision: keep it", "owner decision: keep it, Bob (DECISION-4)",
                 "owner decision: keep it, Matthew", "owner decision: pending", "owner decision: pending (DECISION-2)",
                 "open", "TODO", "won't fix"):
        assert R.parse_disposition(cell) == (None, None), cell


def t_globs_and_merge_hold_list():
    rx = R.glob_regex
    assert rx(".github/workflows/**").fullmatch(".github/workflows/ci.yml")
    assert rx("**/auth/**").fullmatch("auth/x.py") and rx("**/auth/**").fullmatch("src/auth/x/y.py")
    assert not rx("**/auth/**").fullmatch("src/author.py")
    assert rx("**/*secret*").fullmatch("secrets.env") and rx("**/*secret*").fullmatch("config/my_secret.py")
    assert rx("requirements*.txt").fullmatch("requirements-dev.txt") and not rx("requirements*.txt").fullmatch("a/requirements.txt")
    assert rx("tests/**").fullmatch("tests/a/b.py") and not rx("tests/**").fullmatch("tests_x/a.py")
    assert rx("*.py").fullmatch("a.py") and not rx("*.py").fullmatch("x/a.py")
    assert rx("**/test_*").fullmatch("test_a.py") and rx("**/test_*").fullmatch("x/y/test_a.py")
    assert rx("a?c").fullmatch("abc") and not rx("a?c").fullmatch("a/c") and not rx("a.c").fullmatch("abc")
    rules = R.merge_hold_rules(open(os.path.join(TEMPLATES, "PLAYBOOK.md")).read())
    assert len(rules) == 20, rules
    assert {label for label, _, deleted, _ in rules if deleted} == {"Deleted or weakened tests"}
    assert ("CI and workflow files", ".github/workflows/**") in [(r[0], r[1]) for r in rules]
    assert R.merge_hold_rules("# Playbook\n\n## Phases\n") is None
    assert R.merge_hold_rules("## Merge-hold list\n\nNone yet.\n\n## Environment needs\n- `x`\n") == []


def held(rules, path, status="M"):
    """The label of the first merge-hold rule PATH (changed with STATUS) matches, or None."""
    return next((label for label, _, deleted, rx in rules if (status == "D" or not deleted) and rx.fullmatch(path)), None)


def t_template_globs_match_nested_paths():  # cold M3 R1-1
    rules = R.merge_hold_rules(open(os.path.join(TEMPLATES, "PLAYBOOK.md")).read())
    for path in ("package.json", "web/package.json", "requirements.txt", "svc/requirements-dev.txt", "lib/go.mod",
                 "go.mod", "crates/x/Cargo.toml", "pyproject.toml", "tools/setup.py", "api/Pipfile"):
        assert held(rules, path) == "New dependencies", path
    for path in ("tests/test_old.py", "pkg/tests/helpers.py", "web/src/a.test.js", "src/__tests__/a.js", "test_x.py",
                 "pkg/x_test.go", "test/unit/a.rb"):
        assert held(rules, path, "D") == "Deleted or weakened tests", path
        assert held(rules, path, "M") is None, path  # adding or editing tests never holds
    assert held(rules, "src/app.py") is None and held(rules, "web/packages.json") is None


def t_blank_line_inside_a_table():  # cold M3 R1-12
    text = ("| ID | severity |\n| --- | --- |\n| R1-1 | low |\n\n| R1-2 | high |\n\nnone\n\n"
            "| criterion | met |\n| --- | --- |\n| P1 | yes |\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
    tables = R.md_tables(text)
    assert [(h, rows) for h, rows in tables] == [
        (["id", "severity"], [["R1-1", "low"], ["R1-2", "high"]]), (["criterion", "met"], [["P1", "yes"]]),
        (["a", "b"], [["1", "2"]])], tables
    report = cold_report(1, "c" * 40, [("R1-1", "low", "app.py:1"), ("R1-2", "high", "app.py:2")])
    report = report.replace("| R1-1 | low | app.py:1 | a finding | it breaks |\n",
                            "| R1-1 | low | app.py:1 | a finding | it breaks |\n\n")
    assert R.parse_cold_report("r.md", "round", 1, report)["findings"] == {"R1-1": "low", "R1-2": "high"}


def t_wrapped_merge_hold_bullet():  # cold M3 R1-11
    playbook = ("## Merge-hold list\n\nHeld for Matthew.\n\n"
                "- CI and workflow files: `.github/actions/**`,\n    `.github/workflows/**`\n"
                "- Deleted or weakened tests:\n\n  `**/tests/**`\n"
                "Not a bullet: `ignored/**`\n\n## Environment needs\n")
    rules = R.merge_hold_rules(playbook)
    assert [(label, glob) for label, glob, _, _ in rules] == [
        ("CI and workflow files", ".github/actions/**"), ("CI and workflow files", ".github/workflows/**"),
        ("Deleted or weakened tests", "**/tests/**")], rules
    assert held(rules, ".github/workflows/ci.yml") == "CI and workflow files"
    assert held(rules, "pkg/tests/a.py", "D") == "Deleted or weakened tests" and held(rules, "ignored/x") is None


# --- gate: each check

def t_gate_passes():
    s = mission()
    r = gate()
    assert r.returncode == 0, out(r)
    for name in ("PR", "lease", "coverage", "dispositions", "checks", "sensitive paths"):
        passed(r, name)
    assert f"round-2.md covers {s['c2'][:12]}; only review records changed since" in line(r, "coverage"), out(r)
    assert "no checks configured" in line(r, "checks")
    assert "2 cold and 2 Qodo row(s)" in line(r, "dispositions")
    assert verdict(r) == f"gate: PASS {s['head']}"


def t_record_only_commit_after_review():
    s = mission()
    start(base=s["head"])
    commit("review: qodo fetch 2, dispositions", dict(
        qodo_archive(2, QODO_FINDINGS, s["c2"]),
        **{f"reviews/qodo/PR-{PR}/DISPOSITIONS.md": qodo_dispositions(default_qodo_rows(s), reviewed=s["c2"],
                                                                      fetches="1, 2")}))
    top = publish()
    r = gate()
    assert r.returncode == 0 and verdict(r) == f"gate: PASS {top}", out(r)


def t_code_after_review_needs_scoped_review():
    s = mission()
    start(base=s["head"])
    c3 = commit("feat: farewell", {"app.py": APP2 + "def bye():\n    return 'bye'\n"})
    publish()
    r = gate()
    assert r.returncode == 6, out(r)
    failed(r, "coverage", f"(reviews/cold/M3/round-2.md, {s['c2'][:12]}): app.py;", "scoped cold review")
    assert verdict(r) == "gate: FAIL hold reasons none; fix first: coverage"
    commit("review: scoped 1", {"reviews/cold/M3/scoped-1.md": cold_report(1, c3, kind="scoped", since=s["c2"])})
    publish()
    r = gate()
    assert r.returncode == 0, out(r)
    assert f"scoped-1.md covers {c3[:12]}" in line(r, "coverage")


def t_uncovered_files_under_reviews():
    s = mission()
    start(base=s["head"])
    sneaky = ["reviews/cold/M3/notes.md", "reviews/run.py", f"reviews/qodo/PR-{PR}/1/helper.py",
              "reviews/cold/M3/round-1.md.orig"]
    commit("not records", {p: "print('hi')\n" for p in sneaky})
    publish()
    r = gate()
    assert r.returncode == 6, out(r)
    failed(r, "coverage", *sneaky)
    listed = line(r, "coverage").split("): ", 1)[1].split("; ")[0].split(", ")
    assert sorted(listed) == sorted(sneaky), listed


def t_coverage_without_any_review():
    start()
    commit("feat", {"app.py": APP1})
    publish()
    r = gate()
    assert r.returncode == 6, out(r)
    failed(r, "coverage", "no recorded review")
    failed(r, "dispositions", "reviews/cold/M3/DISPOSITIONS.md is missing",
           f"reviews/qodo/PR-{PR}/DISPOSITIONS.md is missing (QODO_REVIEW=on)")


def t_coverage_bad_covers():
    start()
    c1 = commit("feat", {"app.py": APP1})
    commit("records", {"reviews/cold/M3/round-1.md": cold_report(1, c1[:12]),
                       "reviews/cold/M3/round-2.md": cold_report(2, "0" * 40),
                       "reviews/cold/M3/DISPOSITIONS.md": cold_dispositions([]),
                       f"reviews/qodo/PR-{PR}/DISPOSITIONS.md": qodo_dispositions([], qodo="no first review")})
    publish()
    r = gate()
    assert r.returncode == 6, out(r)
    failed(r, "coverage", "round-1.md: 'covers:' must name", "no recorded review covers a commit of this branch",
           "round-2.md covers 000000000000")
    passed(r, "dispositions")


def t_qodo_review_alone_covers():
    start()
    c1 = commit("feat", {"app.py": APP1})
    commit("records", dict(qodo_archive(1, [("Informational", "Greeting text is hard-coded", False)], c1), **{
        "reviews/cold/M3/DISPOSITIONS.md": cold_dispositions([]),
        f"reviews/qodo/PR-{PR}/DISPOSITIONS.md": qodo_dispositions(
            [("1", "Informational", "greeting TEXT is `hard-coded`", "app.py", "dismissed: fixed by the playbook")],
            reviewed=c1)}))
    publish()
    r = gate()
    assert r.returncode == 0, out(r)
    assert f"Qodo fetch 1 covers {c1[:12]}" in line(r, "coverage")


def t_every_disposition_form_passes():
    def rows(s):
        return [("R1-1", "high", "app.py:2", f"fixed in {s['c2'][:7]}"),
                ("R1-2", "medium", "app.py", "dismissed: test_greet shows the empty name works"),
                ("R1-3", "low", "app.py", "deferred: L-1 to M4"),
                ("R1-4", "medium", "n/a", "deferred: L-2 to phase 2 backlog"),
                ("R1-5", "high", "app.py", "owner decision: keep the greeting, Matthew (DECISION-3)"),
                ("R1-6", "low", "`app.py`, lib/", f"fixed in {s['c2']}")]

    def qrows(s):
        return [("1", "Action required", "crash WHEN the name is missing", "app.py", f"fixed in {s['c2']}"),
                ("2", "Informational", "Greeting text is hard-coded", "", "deferred: L-2 to phase 2 backlog"),
                ("absent", "Action required", "An old finding", "app.py",
                 "owner decision: not a bug, Matthew (DECISION-3)")]

    found = [(f"R1-{i}", sev, "app.py:1") for i, sev in enumerate(("high", "medium", "low", "medium", "high", "low"), 1)]
    mission(findings1=found, cold_rows=rows, qodo_rows=qrows)
    r = gate()
    assert r.returncode == 0, out(r)
    assert "6 cold and 3 Qodo row(s)" in line(r, "dispositions")


def t_disposition_failures():
    g("checkout", "-q", "-B", "side", "origin/main")
    side = commit("elsewhere", {"other.py": "x = 1\n"})

    def rows(s):
        return [("R1-1", "high", "app.py", "dismissed: works for me"),
                ("R1-2", "high", "app.py", "deferred: L-1 to M4"),
                ("R1-3", "medium", "app.py", "owner decision: pending (ESCALATION-4)"),
                ("R1-4", "low", "app.py", "will look later"),
                ("R1-5", "low", "app.py", ""),
                ("R1-6", "medium", "app.py", "deferred: L-99 to M4"),
                ("R1-7", "medium", "other.py", f"fixed in {side[:7]}"),
                ("R1-8", "low", "lib/util.py", f"fixed in {s['c2'][:7]}"),
                ("R1-9", "low", "app.py", "fixed in deadbee"),
                ("R1-10", "low", "app.py", "dismissed: the row says low, the report says high")]

    found = [(f"R1-{i}", "high" if i in (1, 2, 10) else "low", "app.py:1") for i in range(1, 11)]
    mission(findings1=found, findings2=[("R2-1", "medium", "app.py:2")], cold_rows=rows)
    r = gate()
    assert r.returncode == 6, out(r)
    failed(r, "dispositions",
           "cold R1-1 is top severity, so only a fix or an owner decision closes it, not 'dismissed'",
           "cold R1-2 is top severity, so only a fix or an owner decision closes it, not 'deferred'",
           "cold R1-3 waits on an open owner decision (ESCALATION-4)",
           "cold R1-4 is undecided ('will look later')", "cold R1-5 is undecided;",
           "cold R1-6: L-99 is not in docs/playbook/LEDGER.md",
           f"cold R1-7: fixed in {side[:7]}, which is not an ancestor of HEAD",
           "cold R1-8: fixed in", "which doesn't touch lib/util.py", "cold R1-9: fixed in deadbee: no such commit",
           "cold R1-10 is top severity", "has no row for R2-1")
    assert verdict(r) == "gate: FAIL hold reasons 1, 2; fix first: dispositions"
    # an open owner decision alone holds, with nothing for the lead to fix
    mission(cold_rows=lambda s: [("R1-1", "high", "app.py", "owner decision: pending (ESCALATION-2)"),
                                 ("R1-2", "low", "app.py", "dismissed: checked by the caller")])
    r = gate()
    assert verdict(r) == "gate: FAIL hold reasons 1", out(r)
    mission(cold_rows=lambda s: [("R1-1", "high", "app.py", f"fixed in {s['c2'][:7]}"), ("R1-2", "low", "app.py", "?")])
    r = gate()
    assert verdict(r) == "gate: FAIL hold reasons 2", out(r)


def t_cold_report_problems():
    mission(findings1=[("R1-1", "high", "app.py:2"), ("R2-7", "low", "app.py:1"), ("R1-3", "urgent", "app.py:1")],
            cold_rows=lambda s: [("R1-1", "high", "app.py", f"fixed in {s['c2'][:7]}"),
                                 ("R2-7", "low", "app.py", "dismissed: x"), ("R1-3", "high", "app.py", f"fixed in {s['c2'][:7]}")])
    r = gate()
    failed(r, "dispositions", "finding ID R2-7 is not R1-<n>", "R1-3 has severity 'urgent', not high, medium or low")
    assert verdict(r) == "gate: FAIL hold reasons none; fix first: dispositions", out(r)


def t_finding_after_a_blank_line_needs_a_row():  # cold M3 R1-12
    s = mission(findings1=[("R1-1", "low", "app.py:1"), ("R1-2", "high", "app.py:2")],
                cold_rows=lambda s: [("R1-1", "low", "app.py", "dismissed: checked by the caller")])
    start(base=s["head"])
    report = cold_report(1, s["c1"], [("R1-1", "low", "app.py:1"), ("R1-2", "high", "app.py:2")])
    commit("review: reflow round 1", {"reviews/cold/M3/round-1.md": report.replace("it breaks |\n| R1-2", "it breaks |\n\n| R1-2")})
    publish()
    failed(gate(), "dispositions", "reviews/cold/M3/DISPOSITIONS.md has no row for R1-2")


def t_qodo_dispositions():
    mission(qodo="off", qodo_file=False)
    r = gate(QODO_REVIEW="off")
    assert r.returncode == 0, out(r)
    r = gate()
    failed(r, "dispositions", f"reviews/qodo/PR-{PR}/DISPOSITIONS.md is missing (QODO_REVIEW=on)")
    r = gate(QODO_REVIEW="maybe")
    failed(r, "dispositions", "QODO_REVIEW must be on or off, not 'maybe'")
    mission(qodo="no first review")
    r = gate()
    assert r.returncode == 0, out(r)
    # qodo: on needs a row for every finding of the latest archive, and the severity rule holds for Qodo too
    three = QODO_FINDINGS + [("Remediation recommended", "Logs the user's name", False)]
    mission(qodo_findings=three)
    r = gate()
    failed(r, "dispositions", f"DISPOSITIONS.md has no row for: Logs the user's name (archive fetch 1)")
    mission(qodo_rows=lambda s: [("1", "Informational", "Crash when the name is missing", "app.py", "dismissed: no crash"),
                                 ("2", "Informational", "Greeting text is hard-coded", "app.py", "dismissed: by design")])
    r = gate()
    failed(r, "dispositions", 'Qodo #1 "Crash when the name is missing" is top severity')
    assert verdict(r) == "gate: FAIL hold reasons 1", out(r)
    s = mission(qodo_rows=lambda s: default_qodo_rows(s)[:1] + [("2", "Informational", "Greeting text is hard-coded",
                                                                 "lib/util.py", f"fixed in {s['c2'][:7]}")])
    r = gate()
    failed(r, "dispositions", f'Qodo #2 "Greeting text is hard-coded": fixed in {s["c2"][:7]}, which doesn\'t touch lib/util.py')


def t_checks():
    s = mission()
    sha = s["head"]

    def run(name, status="completed", conclusion="success", id=1):
        return {"id": id, "name": name, "status": status, "conclusion": conclusion if status == "completed" else None}

    gh_cfg(check_runs={sha: [run("ci"), run("docs", conclusion="skipped", id=2), run("lint", conclusion="neutral", id=3)]})
    r = gate()
    assert r.returncode == 0 and "3 passed" in line(r, "checks"), out(r)
    gh_cfg(check_runs={sha: [run("ci", conclusion="failure", id=1), run("ci", id=2)]})  # a re-run replaces a failure
    assert gate().returncode == 0
    gh_cfg(check_runs={sha: [run("ci", conclusion="failure"), run("lint", conclusion="timed_out", id=2)]})
    r = gate()
    assert r.returncode == 6, out(r)
    failed(r, "checks", "failed: ci, lint")
    assert verdict(r) == "gate: FAIL hold reasons 3"
    gh_cfg(check_runs={sha: [run("ci"), run("e2e", status="in_progress", id=2)]})
    r = gate()
    assert r.returncode == 3 and verdict(r) == "gate: WAIT checks: pending: e2e", out(r)
    assert line(r, "checks").startswith("… ")
    gh_cfg(check_runs={sha: [run("ci")]}, statuses={sha: [{"context": "lint", "state": "success"}]},
           protection={"required_status_checks": {"contexts": ["lint"], "checks": [{"context": "ci"}]}})
    r = gate()
    assert r.returncode == 0 and "(required: ci, lint)" in line(r, "checks"), out(r)
    gh_cfg(statuses={sha: []})
    r = gate()
    failed(r, "checks", "required but missing: lint")
    assert verdict(r) == "gate: FAIL hold reasons 3"
    gh_cfg(statuses={sha: [{"context": "lint", "state": "success"}, {"context": "deploy", "state": "error"}]})
    failed(gate(), "checks", "failed: deploy")
    gh_cfg(statuses={sha: [{"context": "lint", "state": "pending"}]})
    assert gate().returncode == 3
    gh_reset()
    gh_cfg(rules=[{"type": "required_status_checks", "ruleset_id": 4,
                   "parameters": {"required_status_checks": [{"context": "e2e"}]}}])
    failed(gate(), "checks", "required but missing: e2e")
    gh_reset()
    gh_cfg(protection={"_status": 403, "message": "Resource not accessible by integration"})
    r = gate()
    failed(r, "checks", "can't read main's protection")
    assert verdict(r) == "gate: FAIL hold reasons none; fix first: checks"
    upgrade = {"_status": 403, "message": "Upgrade to GitHub Pro or make this repository public to enable this feature."}
    gh_cfg(protection=upgrade, rules=upgrade)
    r = gate()
    assert r.returncode == 0 and "no checks configured" in line(r, "checks"), out(r)
    gh_reset()


def t_sensitive_paths():
    mission(extra={".github/workflows/ci.yml": "on: push\n"})
    r = gate()
    assert r.returncode == 6, out(r)
    failed(r, "sensitive paths", ".github/workflows/ci.yml (`.github/workflows/**`, CI and workflow files)")
    assert verdict(r) == "gate: FAIL hold reasons 5"
    mission(extra={"tests/test_old.py": None})
    r = gate()
    failed(r, "sensitive paths", "tests/test_old.py (deleted; `**/tests/**`, Deleted or weakened tests)")
    assert verdict(r) == "gate: FAIL hold reasons 5", out(r)
    # nested manifests and a deleted nested test hold too (cold M3 R1-1)
    mission(extra={"web/package.json": "{}\n", "svc/requirements.txt": "evil==1\n", "lib/tests/test_x.py": None})
    r = gate()
    failed(r, "sensitive paths", "web/package.json (`**/package.json`, New dependencies)",
           "svc/requirements.txt (`**/requirements*.txt`, New dependencies)",
           "lib/tests/test_x.py (deleted; `**/tests/**`, Deleted or weakened tests)")
    mission(extra={"tests/test_old.py": "def test_greet():\n    assert True\n", "tests/test_new.py": "x = 1\n",
                   "src/test_util.py": "x = 2\n"})
    r = gate()
    assert r.returncode == 0, out(r)
    assert "none on the merge-hold list" in line(r, "sensitive paths")
    original = edit_state("PLAYBOOK.md", lambda t: re.sub(r"## Merge-hold list.*?(?=## Environment needs)", "", t, flags=re.S))
    try:
        r = gate()
        failed(r, "sensitive paths", "has no merge-hold list", "the gate never runs without it")
        assert verdict(r) == "gate: FAIL hold reasons none; fix first: sensitive paths", out(r)
        edit_state("PLAYBOOK.md", lambda t: original.replace("`", ""))
        failed(gate(), "sensitive paths", "has no merge-hold globs")
    finally:
        edit_state("PLAYBOOK.md", lambda t: original)
    assert gate().returncode == 0


def t_allow_hold():
    s = mission(extra={".github/workflows/ci.yml": "on: push\n"})
    r = gate("--allow-hold", "5")
    assert r.returncode == 1 and "go together" in r.stderr, out(r)
    r = gate("--allow-hold", "5", "--decision", "DECISION-7")
    assert r.returncode == 6, out(r)
    failed(r, "sensitive paths", "--allow-hold 5 names DECISION-7, but room 1 has no trusted architect comment DECISION-7")
    assert verdict(r) == "gate: FAIL hold reasons 5"
    room("say", "1", "architect", "DECISION-7: merge the CI change", check=True, FAKE_GH_LOGIN="mallory")
    post_raw("<!-- agent-room role=lead session=L1 -->\n**[lead · L1]**\n\nDECISION-7: forged by a lead")
    room("say", "1", "architect", "DECISION-6: something else", check=True)
    r = gate("--allow-hold", "5", "--decision", "DECISION-7")
    assert r.returncode == 6, "neither an untrusted author nor a lead's comment counts\n" + out(r)
    room("say", "1", "architect", "DECISION-7: merge the CI change", check=True)
    r = gate("--allow-hold", "5", "--decision", "DECISION-7")
    assert r.returncode == 0 and verdict(r) == f"gate: PASS {s['head']}", out(r)
    assert "allowed by DECISION-7" in line(r, "sensitive paths")
    post_raw("DECISION-8: fine, merge it")  # Matthew from GitHub, untagged
    assert gate("--allow-hold", "5", "--decision", "DECISION-8").returncode == 0
    assert gate().returncode == 6, "without --allow-hold the match still holds"


def t_pr_check():
    s = mission()
    for kw, needle in ((dict(state="closed"), "is closed, not open"), (dict(state="closed", merged=True), "is merged"),
                       (dict(base="develop"), "has base develop, not main"),
                       (dict(repo="mallory/pet"), "has its head in mallory/pet"),
                       (dict(ref="feature/x"), "has head feature/x, not a mission/M<k>-… branch")):
        set_pr(s["head"], **kw)
        r = gate()
        assert r.returncode == 6, out(r)
        failed(r, "PR", needle)
        assert verdict(r) == "gate: FAIL hold reasons none; fix first: PR"
    set_pr(s["c2"])  # the PR says one head, origin has another
    failed(gate(), "PR", "it moved")
    g("push", "-q", "-f", "origin", "HEAD:refs/heads/mission/gate-x")
    set_pr(s["head"], ref="mission/gate-x")
    failed(gate(), "PR", "not a mission/M<k>-… branch")
    r = gate("--mission", "M3")
    assert r.returncode == 0 and "(mission M3)" in line(r, "PR"), out(r)
    r = room("gate", "99")
    assert r.returncode == 1 and "github error" in r.stderr, out(r)
    set_pr(s["head"])


def t_lease_lost():
    mission()
    r = gate(ROOM_SESSION="L2")
    assert r.returncode == 5, out(r)
    assert line(r, "lease").startswith("✗ lease: held by L1") and verdict(r) == "gate: lease lost"


# --- merge

def t_merge():
    s = mission()
    sha = s["head"]
    open(CALLS, "w").close()
    r = room("merge", PR, "--sha", s["c2"])
    assert r.returncode == 3 and "head moved: re-run gate" in r.stdout and calls() == [], out(r)
    gh_cfg(check_runs={sha: [{"id": 1, "name": "ci", "status": "completed", "conclusion": "failure"}]})
    r = room("merge", PR, "--sha", sha)
    assert r.returncode == 6 and calls() == [] and block()["intent"] == "none", out(r)
    gh_reset()
    r = room("merge", PR, "--sha", sha, ROOM_SESSION="L2")
    assert r.returncode == 5 and calls() == [], out(r)
    gh_cfg(merge={"_status": 409, "message": "Head branch was modified. Review and try the merge again."})
    r = room("merge", PR, "--sha", sha)
    assert r.returncode == 3 and "head moved: re-run gate" in r.stdout, out(r)
    assert calls()[-1] == {"pr": PR, "sha": sha, "merge_method": "merge"} and block()["intent"] == "none"
    gh_cfg(merge={"_status": 405, "message": "Pull Request is not mergeable"})
    r = room("merge", PR, "--sha", sha)
    assert r.returncode == 6 and "not mergeable" in r.stdout and block()["intent"] == "none", out(r)
    gh_cfg(merge={"_status": 502, "message": "Bad Gateway"})
    r = room("merge", PR, "--sha", sha)
    assert r.returncode == 1 and "intent left recorded" in r.stderr, out(r)
    assert block()["intent"] == f"merge PR #{PR} at {sha}" and block()["pr"] == "none"
    gh_reset()
    n = len(calls())
    r = room("merge", PR, "--sha", sha)
    assert r.returncode == 0, out(r)
    assert verdict(r) == f"gate: PASS {sha}" and re.search(rf"^merged PR #{PR}: [0-9a-f]{{40}}$", r.stdout, re.M), out(r)
    assert len(calls()) == n + 1 and calls()[-1] == {"pr": PR, "sha": sha, "merge_method": "merge"}
    b = block()
    assert b["intent"] == "none" and b["pr"] == f"merged:{PR}", b
    r = room("merge", PR, "--sha", "abc")
    assert r.returncode == 2 and "40-hex" in r.stderr, out(r)


setup()
for name, fn in list(globals().items()):
    if name.startswith("t_"):
        test(name[2:], fn)
shutil.rmtree(tmp, ignore_errors=True)
print("all passed")
