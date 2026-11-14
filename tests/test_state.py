#!/usr/bin/env python3
"""Tests for room.py's state branch, lead lease and preflight. Run: python3 tests/test_state.py

Each project repo is a local bare git repo standing in for GitHub; `gh` is fake_gh_state.py.
Machine A works inside a checkout of the project (state worktree via `git worktree add`);
machine B has no checkout (state worktree is a clone of $ROOM_STATE_REMOTE).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ROOM = os.path.join(ROOT, "room.py")
TEMPLATES = os.path.join(ROOT, "templates", "playbook")
tmp = tempfile.mkdtemp(prefix="room-state-")
BIN = os.path.join(tmp, "bin")
HOME = os.path.join(tmp, "home")  # no git identity here, so room.py's fallback identity is exercised
GH_CFG = os.path.join(tmp, "gh-state.json")
for d in (BIN, HOME):
    os.makedirs(d)


def shim(bindir, name, target):
    path = os.path.join(bindir, name)
    with open(path, "w") as f:
        f.write(f'#!/bin/sh\nexec "{sys.executable}" "{target}" "$@"\n')
    os.chmod(path, 0o755)


shim(BIN, "gh", os.path.join(HERE, "fake_gh_state.py"))

ENV = {k: v for k, v in os.environ.items()
       if not k.startswith(("ROOM_", "GIT_", "QODO_", "CLAUDE_CODE_SESSION"))}
ENV.update(PATH=BIN + os.pathsep + os.environ["PATH"], HOME=HOME, XDG_CONFIG_HOME=os.path.join(HOME, ".config"),
           GIT_CONFIG_NOSYSTEM="1", FAKE_GH_DB=os.path.join(tmp, "db.json"), FAKE_GH_STATE=GH_CFG,
           ROOM_REPO="SigorMatt/pet", ROOM_STATE=os.path.join(tmp, "cursors"))
GIT_ENV = dict(ENV, GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="test@example.com",
               GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="test@example.com")


def g(*args, cwd=None, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, env=GIT_ENV, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise AssertionError(f"git {args} failed: {r.stderr}")
    return r


def bare(name):
    path = os.path.join(tmp, "git", "SigorMatt", name + ".git")  # /git/OWNER/NAME, like the proxy's URLs
    g("init", "-q", "--bare", "--initial-branch=main", path)
    return path


PET = bare("pet")
CHECKOUT = os.path.join(tmp, "work", "pet")
g("clone", "-q", PET, CHECKOUT)


def sdir(name):
    return os.path.join(tmp, "state", name)


def room(*args, session="A", state="A", cwd=CHECKOUT, stdin=None, check=True, script=ROOM, **env):
    e = dict(ENV)
    if session:
        e["ROOM_SESSION"] = session
    if state:
        e["ROOM_STATE_DIR"] = sdir(state)
    for k, v in env.items():
        if v is None:
            e.pop(k, None)
        else:
            e[k] = v
    r = subprocess.run([sys.executable, script, *args], env=e, cwd=cwd, input=stdin, capture_output=True,
                       text=True, timeout=120)
    if check and r.returncode != 0:
        raise AssertionError(f"{args} exited {r.returncode}:\n{r.stdout}\n{r.stderr}")
    return r


def room_b(*args, **kw):  # machine B: no checkout, clone of the bare repo
    kw.setdefault("session", "B")
    kw.setdefault("state", "B")
    kw.setdefault("cwd", tmp)
    kw.setdefault("ROOM_STATE_REMOTE", PET)
    return room(*args, **kw)


def remote_file(repo, name, ref="agent-room/state"):
    r = g("--git-dir", repo, "show", f"{ref}:{name}", check=False)
    return r.stdout if r.returncode == 0 else None


def sha(repo, ref):
    return g("--git-dir", repo, "rev-parse", ref).stdout.strip()


def block(repo=PET):
    text = remote_file(repo, "docs/playbook/MISSIONS.md")
    body = text.split("```agent-room-state\n", 1)[1].split("```", 1)[0]
    return dict(line.split(": ", 1) if ": " in line else (line.rstrip(":"), "") for line in body.splitlines())


def playbook_path(state="A", name="PLAYBOOK.md"):
    return os.path.join(sdir(state), "docs", "playbook", name)


def gh_cfg(**cfg):
    with open(GH_CFG, "w") as f:
        json.dump(cfg, f)


def line(r, key):
    for ln in r.stdout.splitlines():
        if key in ln:
            return ln
    raise AssertionError(f"no line with {key!r} in:\n{r.stdout}")


def expect(r, key, mark):
    ln = line(r, key)
    assert ln.startswith(mark + " "), f"expected {mark} for {key!r}, got: {ln}\n{r.stdout}"


def test(name, fn):
    fn()
    print(f"ok  {name}")


# --- state branch

def t_preflight_on_empty_repo():
    gh_cfg()
    r = room("preflight", "--role", "architect", check=False)
    assert r.returncode == 1, r.stdout
    expect(r, "push access", "✓")
    expect(r, "main has no commits", "✗")
    assert "state init" in line(r, "main has no commits")
    expect(r, "state branch", "✗")
    assert "preflight failed" in r.stdout
    r = room("preflight", "--role", "lead", check=False)
    expect(r, "lead-owned files", "✗")
    assert not os.path.exists(sdir("A")), "preflight must not create a worktree for a missing branch"


def t_state_init_on_empty_repo():
    r = room("state", "init", session="arch")
    assert "created main" in r.stdout and "created agent-room/state" in r.stdout, r.stdout
    assert sorted(g("--git-dir", PET, "ls-tree", "--name-only", "main").stdout.split()) == [".gitignore", "README.md"]
    assert remote_file(PET, "README.md", "main") == "# pet\n"
    files = g("--git-dir", PET, "ls-tree", "-r", "--name-only", "agent-room/state").stdout.split()
    assert sorted(files) == ["docs/playbook/DESIGN.md", "docs/playbook/HANDOFF.md", "docs/playbook/PLAYBOOK.md"], files
    playbook = remote_file(PET, "docs/playbook/PLAYBOOK.md")
    assert "\nrepo: SigorMatt/pet\n" in playbook and "\npipeline: main\n" in playbook, playbook
    assert g("--git-dir", PET, "merge-base", "main", "agent-room/state", check=False).returncode == 1, "must be orphan"
    assert g("--git-dir", PET, "log", "-1", "--format=%an", "agent-room/state").stdout.strip() == "agent-room"
    assert os.path.isfile(os.path.join(sdir("A"), ".git")), "inside a checkout the state dir is a git worktree"
    assert g("-C", sdir("A"), "rev-parse", "HEAD").stdout.strip() == sha(PET, "agent-room/state")
    assert r.stdout.strip().endswith(sdir("A"))


def t_state_init_is_idempotent():
    before = (sha(PET, "main"), sha(PET, "agent-room/state"))
    r = room("state", "init", session="arch")
    assert "created" not in r.stdout and "added" not in r.stdout, r.stdout
    r = room_b("state", "init")  # a second machine with no checkout
    assert "created" not in r.stdout and "added" not in r.stdout, r.stdout
    assert os.path.isdir(os.path.join(sdir("B"), ".git")), "without a checkout the state dir is a clone"
    assert (sha(PET, "main"), sha(PET, "agent-room/state")) == before
    # a missing architect file comes back
    os.remove(playbook_path("B", "HANDOFF.md"))
    room_b("state", "commit", "-m", "drop handoff")
    assert remote_file(PET, "docs/playbook/HANDOFF.md") is None
    r = room("state", "init", session="arch")
    assert "added HANDOFF.md" in r.stdout, r.stdout
    assert remote_file(PET, "docs/playbook/HANDOFF.md")


def t_state_init_on_existing_repo():
    old = bare("old")
    seed = os.path.join(tmp, "seed")
    g("init", "-q", "--initial-branch=main", seed)
    open(os.path.join(seed, "app.py"), "w").write("print('legacy')\n")
    g("add", "-A", cwd=seed)
    g("commit", "-q", "-m", "legacy code", cwd=seed)
    g("push", "-q", old, "main", cwd=seed)
    main_before = sha(old, "main")
    kw = dict(session="arch", state="old", cwd=tmp, ROOM_REPO="SigorMatt/old", ROOM_STATE_REMOTE=old)
    r = room("state", "init", **kw)
    assert "created main" not in r.stdout and "created agent-room/state" in r.stdout, r.stdout
    assert sha(old, "main") == main_before
    assert "repo: SigorMatt/old" in remote_file(old, "docs/playbook/PLAYBOOK.md")
    state_before = sha(old, "agent-room/state")
    r = room("state", "init", **kw)
    assert "created" not in r.stdout and sha(old, "agent-room/state") == state_before, r.stdout
    # a repo with branches but no main is left alone
    weird = bare("weird")
    g("push", "-q", weird, "main:master", cwd=seed)
    r = room("state", "init", session="arch", state="weird", cwd=tmp, ROOM_REPO="SigorMatt/weird",
             ROOM_STATE_REMOTE=weird, check=False)
    assert r.returncode == 1 and "no main branch" in r.stderr, r.stderr
    assert remote_file(weird, "docs/playbook/PLAYBOOK.md") is None


def t_state_init_lead():
    r = room("state", "init-lead", session="L1")
    assert "added MISSIONS.md, LEDGER.md, QODO-VALUE.md" in r.stdout, r.stdout
    for n in ("MISSIONS.md", "LEDGER.md", "QODO-VALUE.md", "PLAYBOOK.md"):
        assert remote_file(PET, f"docs/playbook/{n}"), n
    b = block()
    assert b["lease_session"] == "none" and b["lease_generation"] == "0" and b["counter"] == "0", b
    assert list(b) == ["lease_session", "lease_generation", "phase", "room", "mission", "step", "pr", "cursor",
                       "counter", "intent", "waiting_for_owner"], list(b)
    before = sha(PET, "agent-room/state")
    r = room_b("state", "init-lead")
    assert "already present" in r.stdout and sha(PET, "agent-room/state") == before, r.stdout


def t_state_set_and_get():
    r = room("state", "set", "phase=2", "mission=M1", "custom_key=hello world")
    assert "set phase=2 mission=M1 custom_key=hello world" in r.stdout, r.stdout
    b = block()
    assert b["phase"] == "2" and b["mission"] == "M1" and b["custom_key"] == "hello world", b
    assert list(b)[0] == "lease_session" and list(b)[-1] == "custom_key", "order kept, new keys appended"
    assert room_b("state", "get", "custom_key").stdout.strip() == "hello world"  # B syncs before reading
    assert room_b("state", "get", "phase").stdout.strip() == "2"
    room("state", "set", "custom_key=changed")
    assert block()["custom_key"] == "changed" and block()["phase"] == "2", "unknown keys are kept and editable"
    for bad, why in (("noequals", "KEY=VALUE"), ("Phase=1", "KEY=VALUE"), ("intent=a\nb", "single line")):
        r = room("state", "set", bad, check=False)
        assert r.returncode == 1 and why in r.stderr, (bad, r.stderr)
    r = room("state", "get", "no_such_key", check=False)
    assert r.returncode == 1 and "no key" in r.stderr, r.stderr


def t_state_next_counter():
    assert room("state", "next", "counter").stdout.strip() == "1"
    assert room_b("state", "next", "counter").stdout.strip() == "2"
    assert room("state", "next", "counter").stdout.strip() == "3"  # A syncs first, so no race
    assert block()["counter"] == "3"
    r = room("state", "next", "mission", check=False)  # "M1" is not a number
    assert r.returncode == 1 and "not a number" in r.stderr, r.stderr


def t_state_commit_rejected_after_another_push():
    room("state", "sync")
    room_b("state", "sync")
    with open(playbook_path("B", "LEDGER.md"), "a") as f:
        f.write("| L-1 | cold M1 | from B | real | M2 | open |\n")
    assert "pushed" in room_b("state", "commit", "-m", "ledger: L-1").stdout
    with open(playbook_path("A", "LEDGER.md"), "a") as f:
        f.write("| L-9 | cold M1 | from A | stale | M2 | open |\n")
    r = room("state", "commit", "-m", "ledger: L-9", check=False)
    assert r.returncode == 3 and "state moved: run 'state sync', re-read, re-apply" in r.stderr, (r.returncode, r.stderr)
    ledger = open(playbook_path("A", "LEDGER.md")).read()
    assert "L-1" in ledger and "L-9" not in ledger, "the worktree is reset to the remote"
    assert g("-C", sdir("A"), "status", "--porcelain").stdout == ""
    assert "L-9" not in remote_file(PET, "docs/playbook/LEDGER.md")
    assert "nothing to commit" in room("state", "commit", "-m", "noop").stdout


def t_local_work_is_not_discarded_silently():
    with open(playbook_path("A", "LEDGER.md"), "a") as f:
        f.write("| L-2 | draft |\n")
    r = room("state", "set", "step=build", check=False)
    assert r.returncode == 1 and "uncommitted changes" in r.stderr, r.stderr
    r = room("state", "path")
    assert r.stdout.strip() == sdir("A") and "not synced" in r.stderr, (r.stdout, r.stderr)
    assert "L-2" in open(playbook_path("A", "LEDGER.md")).read()
    assert "synced" in room("state", "sync").stdout
    assert "L-2" not in open(playbook_path("A", "LEDGER.md")).read()


def t_state_path_default_location():
    r = room("state", "path", state=None)
    path = os.path.join(HOME, "agent-room-state", "SigorMatt__pet")
    assert r.stdout.strip() == path and os.path.isfile(os.path.join(path, ".git")), r.stdout


# --- lease

def t_lease_take_race():
    room("state", "sync")
    room_b("state", "sync")
    gen = int(block()["lease_generation"])
    # B's push is held at its pre-push hook while A takes the lease: B then loses the race
    hooks, out = os.path.join(tmp, "hooks"), os.path.join(tmp, "hook-out.txt")
    os.makedirs(hooks)
    with open(os.path.join(hooks, "pre-push"), "w") as f:
        f.write(f"""#!/bin/sh
cat >/dev/null
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR ROOM_STATE_REMOTE
[ -e "{hooks}/fired" ] && exit 0
touch "{hooks}/fired"
cd "{CHECKOUT}" && ROOM_SESSION=A ROOM_STATE_DIR="{sdir('A')}" "{sys.executable}" "{ROOM}" lease take >"{out}" 2>&1
exit 0
""")
    os.chmod(os.path.join(hooks, "pre-push"), 0o755)
    g("-C", sdir("B"), "config", "core.hooksPath", hooks)
    try:
        r = room_b("lease", "take", check=False)
    finally:
        g("-C", sdir("B"), "config", "--unset", "core.hooksPath")
    assert os.path.exists(os.path.join(hooks, "fired")), "the race hook did not run"
    assert open(out).read().strip() == str(gen + 1), open(out).read()
    assert r.returncode == 3 and "lease not taken" in r.stderr, (r.returncode, r.stdout, r.stderr)
    b = block()
    assert b["lease_session"] == "A" and b["lease_generation"] == str(gen + 1), b
    assert "lease_session: A" in open(playbook_path("B", "MISSIONS.md")).read(), "loser is reset to the remote"
    r = room("lease", "check")
    assert r.returncode == 0 and "this session" in r.stdout, r.stdout
    r = room_b("lease", "check", check=False)
    assert r.returncode == 5 and "held by A" in r.stdout, (r.returncode, r.stdout)
    # without a race, a later take simply wins the next generation
    assert room_b("lease", "take").stdout.strip() == str(gen + 2)
    assert room("lease", "check", check=False).returncode == 5
    assert room_b("lease", "check", session=None, check=False).returncode == 5  # falls back to the hostname
    assert room_b("lease", "check", "--session", "B", session="X").returncode == 0  # --session wins over env
    r = room_b("lease", "check", session=None, CLAUDE_CODE_SESSION_ID="B0123456789", check=False)
    assert r.returncode == 5 and "(B0123456)" in r.stdout, r.stdout


def t_say_refused_without_lease():
    assert "room 1 in SigorMatt/pet" in room("new", "Phase 1").stdout
    room("lease", "take", session="L1")
    r = room("say", "1", "lead", "STATUS: building", session="L2", check=False)
    assert r.returncode == 5 and "held by L1" in r.stderr, (r.returncode, r.stderr)
    r = room("say", "1", "lead", "-", session="L2", stdin="STATUS: from stdin", check=False)
    assert r.returncode == 5, r.stderr
    assert "sent #" in room("say", "1", "lead", "LEAD ONLINE", session="L2").stdout
    assert "sent #" in room("say", "1", "lead", "-", session="L2", stdin="LEAD ONLINE\nvia stdin").stdout
    assert "sent #" in room("say", "1", "lead", "STATUS: holder speaks", session="L1").stdout
    assert "sent #" in room("say", "1", "architect", "DECISION-1: go", session="L2").stdout  # architects aren't leased
    assert "sent #" in room("say", "1", "lead", "STATUS: no worktree", session="L2", state="nowhere").stdout
    transcript = room("read", "1", "--all").stdout
    assert "STATUS: building" not in transcript and "from stdin" not in transcript, transcript
    for text in ("via stdin", "holder speaks", "DECISION-1", "no worktree"):
        assert text in transcript, (text, transcript)


# --- preflight

def set_pipeline(value):
    room("state", "sync")
    text = open(playbook_path()).read()
    lines = [ln for ln in text.splitlines() if not ln.startswith("pipeline:")]
    if value:
        lines.insert(2, f"pipeline: {value}")
    open(playbook_path(), "w").write("\n".join(lines) + "\n")
    room("state", "commit", "-m", f"pipeline {value}")


def t_preflight_architect_passes():
    gh_cfg()
    r = room("preflight", "--role", "architect")
    assert r.returncode == 0 and "preflight passed" in r.stdout, r.stdout
    expect(r, "push access", "✓")
    expect(r, "main has commits", "✓")
    expect(r, "approving reviews", "✓")
    expect(r, "admin bypass", "!")  # no protection at all: reported, never a failure
    expect(r, "deleted automatically", "✓")
    expect(r, "state branch", "!")  # pinned to main, not a release tag
    assert "ROOM_NTFY_TOPIC" not in r.stdout and "lead-owned" not in r.stdout, "lead checks only for the lead"
    set_pipeline("v1.0.0")
    r = room("preflight", "--role", "architect")
    expect(r, "state branch", "✓")
    assert "pinned to v1.0.0" in r.stdout


def t_preflight_state_branch_fails():
    set_pipeline(None)
    r = room("preflight", "--role", "architect", check=False)
    assert r.returncode == 1
    expect(r, "pipeline: v", "✗")
    set_pipeline("v1.0.0")
    os.remove(playbook_path(name="DESIGN.md"))
    room("state", "commit", "-m", "drop design")
    r = room("preflight", "--role", "lead", check=False, ROOM_NTFY_TOPIC="t", QODO_REVIEW="on")
    assert r.returncode == 1
    expect(r, "lacks DESIGN.md", "✗")
    assert "architect commits them" in r.stdout
    room("state", "init", session="arch")
    assert room("preflight", "--role", "architect").returncode == 0


def t_preflight_push_access():
    gh_cfg(repo={"permissions": {"push": False}, "delete_branch_on_merge": True})
    r = room("preflight", "--role", "architect", check=False)
    assert r.returncode == 1
    expect(r, "push access", "✗")
    gh_cfg(repo={"_status": 404, "message": "Not Found"})
    r = room("preflight", "--role", "architect", check=False)
    assert r.returncode == 1 and "can't read SigorMatt/pet" in line(r, "push access")
    expect(r, "push access", "✗")


def t_preflight_delete_branch_on_merge():
    gh_cfg(repo={"permissions": {"push": True}, "delete_branch_on_merge": False})
    r = room("preflight", "--role", "architect")
    assert r.returncode == 0
    expect(r, "Automatically delete head branches", "!")
    assert "Matthew" in line(r, "Automatically delete head branches")
    gh_cfg(repo={"permissions": {"push": True}})
    r = room("preflight", "--role", "architect")
    expect(r, "couldn't read delete_branch_on_merge", "!")


def t_preflight_approving_reviews():
    upgrade = {"_status": 403, "message": "Upgrade to GitHub Pro or make this repository public to enable this feature."}
    gh_cfg(protection=upgrade, rules=upgrade)
    r = room("preflight", "--role", "architect")
    assert r.returncode == 0, r.stdout
    expect(r, "approving reviews", "✓")
    assert "GitHub Free" in line(r, "approving reviews")
    gh_cfg(protection={"_status": 403, "message": "Resource not accessible by integration"})
    r = room("preflight", "--role", "architect", check=False)
    assert r.returncode == 1
    expect(r, "approving reviews", "✗")
    assert "can't read" in line(r, "approving reviews")
    gh_cfg(protection={"required_pull_request_reviews": {"required_approving_review_count": 1},
                       "enforce_admins": {"enabled": False}})
    r = room("preflight", "--role", "architect", check=False)
    assert r.returncode == 1
    expect(r, "approving reviews", "✗")
    assert "classic branch protection (1 approving)" in line(r, "approving reviews")
    expect(r, "admin bypass", "!")
    assert "enforce_admins off" in line(r, "admin bypass")
    gh_cfg(protection={"required_status_checks": {"strict": True, "contexts": ["ci"]},
                       "required_pull_request_reviews": {"required_approving_review_count": 0},
                       "enforce_admins": {"enabled": True}})
    r = room("preflight", "--role", "architect")
    expect(r, "approving reviews", "✓")
    expect(r, "admin bypass", "✓")
    rule = {"type": "pull_request", "ruleset_source_type": "Repository", "ruleset_source": "SigorMatt/pet",
            "ruleset_id": 7, "parameters": {"required_approving_review_count": 2}}
    gh_cfg(rules=[{"type": "deletion", "ruleset_id": 7}, rule],
           rulesets={"7": {"id": 7, "name": "main-guard", "bypass_actors": [
               {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}]}})
    r = room("preflight", "--role", "architect", check=False)
    assert r.returncode == 1
    expect(r, "approving reviews", "✗")
    assert "ruleset 'main-guard' (id 7) (2 approving)" in line(r, "approving reviews"), r.stdout
    expect(r, "admin bypass", "!")
    assert "main-guard' (id 7) has bypass actors: RepositoryRole 5" in line(r, "admin bypass")
    gh_cfg(rules=[{"type": "deletion", "ruleset_id": 8},
                  dict(rule, ruleset_id=8, parameters={"required_approving_review_count": 0})],
           rulesets={"8": {"id": 8, "name": "no-force-push", "bypass_actors": []}})
    r = room("preflight", "--role", "architect")
    expect(r, "approving reviews", "✓")
    expect(r, "admin bypass", "✓")


def t_preflight_lead():
    gh_cfg()
    r = room("preflight", "--role", "lead", ROOM_NTFY_TOPIC="t-secret", QODO_REVIEW="on")
    assert r.returncode == 0, r.stdout
    expect(r, "lead-owned files exist", "✓")
    expect(r, "ROOM_NTFY_TOPIC", "✓")
    expect(r, "QODO_REVIEW is on", "✓")
    assert "t-secret" not in r.stdout, "the topic is private"
    r = room("preflight", "--role", "lead", check=False, QODO_REVIEW="maybe")
    assert r.returncode == 1
    expect(r, "ROOM_NTFY_TOPIC", "✗")
    expect(r, "QODO_REVIEW", "✗")
    # a repo whose lead files don't exist yet: fails, and --fix creates them
    old = os.path.join(tmp, "git", "SigorMatt", "old.git")
    kw = dict(state="old", cwd=tmp, ROOM_REPO="SigorMatt/old", ROOM_STATE_REMOTE=old, ROOM_NTFY_TOPIC="t",
              QODO_REVIEW="off")
    r = room("preflight", "--role", "lead", check=False, **kw)
    assert r.returncode == 1
    expect(r, "lead-owned files missing", "✗")
    assert "MISSIONS.md, LEDGER.md, QODO-VALUE.md" in line(r, "lead-owned files missing")
    r = room("preflight", "--role", "lead", "--fix", **kw)
    assert r.returncode == 0, r.stdout
    expect(r, "lead-owned files exist", "✓")
    assert "--fix created MISSIONS.md, LEDGER.md, QODO-VALUE.md" in r.stdout
    assert remote_file(old, "docs/playbook/MISSIONS.md")


# --- templates for a lone room.py

def t_templates_downloaded_when_alone():
    lone_dir, lone_bin = os.path.join(tmp, "lone"), os.path.join(tmp, "lone-bin")
    os.makedirs(lone_dir)
    os.makedirs(lone_bin)
    shutil.copy(ROOM, os.path.join(lone_dir, "room.py"))
    log = os.path.join(tmp, "tpl-curl.log")
    impl = os.path.join(tmp, "tpl_curl.py")
    with open(impl, "w") as f:
        f.write(f"""import os, sys
url = sys.argv[-1]
open({log!r}, "a").write(url + "\\n")
if os.environ.get("TPL_CURL_FAIL"):
    sys.stderr.write("curl: (22) The requested URL returned error: 404\\n")
    sys.exit(22)
sys.stdout.write(open(os.path.join({TEMPLATES!r}, url.rsplit("/", 1)[1])).read())
""")
    shim(lone_bin, "curl", impl)
    lone = bare("lone")
    kw = dict(session="arch", state="lone", cwd=tmp, script=os.path.join(lone_dir, "room.py"),
              ROOM_REPO="SigorMatt/lone", ROOM_STATE_REMOTE=lone, PATH=lone_bin + os.pathsep + ENV["PATH"])
    r = room("state", "init", check=False, TPL_CURL_FAIL="1", **kw)
    assert r.returncode == 1 and "downloading https://raw.githubusercontent.com/" in r.stderr, r.stderr
    assert g("--git-dir", lone, "ls-remote", "--heads", lone).stdout == "", "a failed download changes nothing"
    open(log, "w").close()
    room("state", "init", **kw)
    urls = open(log).read().split()
    base = "https://raw.githubusercontent.com/SigorMatt/agent-room/main/templates/playbook/"
    assert urls == [base + n for n in ("PLAYBOOK.md", "DESIGN.md", "HANDOFF.md")], urls
    assert remote_file(lone, "docs/playbook/DESIGN.md") == open(os.path.join(TEMPLATES, "DESIGN.md")).read()
    assert "repo: SigorMatt/lone" in remote_file(lone, "docs/playbook/PLAYBOOK.md")


def t_templates_are_short_and_complete():
    for n in ("PLAYBOOK.md", "DESIGN.md", "HANDOFF.md", "MISSIONS.md", "LEDGER.md", "QODO-VALUE.md"):
        text = open(os.path.join(TEMPLATES, n)).read()
        assert len(text.splitlines()) < 60, n
    playbook = open(os.path.join(TEMPLATES, "PLAYBOOK.md")).read()
    for needle in ("pipeline: main", "repo: OWNER/NAME", "room: 0", "test: <command>", "## Phases",
                   "## Items with criteria", "## Merge-hold list", "## Environment needs", "## Lead's discretion",
                   "## Phase 0 known debt", "CI and workflow", "cryptography", "New dependencies",
                   "migrations", "weakened tests"):
        assert needle in playbook, needle
    design = open(os.path.join(TEMPLATES, "DESIGN.md")).read()
    for needle in ("## Goals", "## Non-goals", "## Architecture", "## Interfaces", "## Data", "## Decision log"):
        assert needle in design, needle


for name, fn in list(globals().items()):
    if name.startswith("t_"):
        test(name[2:], fn)
shutil.rmtree(tmp, ignore_errors=True)
print("all passed")
