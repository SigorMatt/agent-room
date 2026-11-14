#!/usr/bin/env python3
"""Tests for room.py's state branch, lead lease and preflight. Run: python3 tests/test_state.py

Each project repo is a local bare git repo standing in for GitHub; `gh` is fake_gh_state.py.
Machine A works inside a checkout of the project (state worktree via `git worktree add`);
machine B has no checkout (state worktree is a clone of $ROOM_STATE_REMOTE).
"""
import contextlib
import json
import os
import re
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


def append(state, name, text):
    with open(playbook_path(state, name), "a") as f:
        f.write(text + "\n")


@contextlib.contextmanager
def pre_push(state, body):
    """A pre-push hook in machine STATE's clone (B-style), for the length of the block."""
    hooks = tempfile.mkdtemp(dir=tmp, prefix="hooks-")
    with open(os.path.join(hooks, "pre-push"), "w") as f:
        f.write("#!/bin/sh\ncat >/dev/null\n"
                "unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR ROOM_STATE_REMOTE\n" + body)
    os.chmod(os.path.join(hooks, "pre-push"), 0o755)
    g("-C", sdir(state), "config", "core.hooksPath", hooks)
    try:
        yield hooks
    finally:
        g("-C", sdir(state), "config", "--unset", "core.hooksPath")


# the push lands, then the client hears a failure (a connection dropped after the remote updated)
LOST_ACK = ('git push -q --no-verify "$2" HEAD:refs/heads/agent-room/state\n'
            'echo "fatal: the remote end hung up unexpectedly" >&2\nexit 1\n')


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
    assert room("lease", "take").stdout.strip() == "1"  # writes to the machine block need the lease
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


def t_state_set_rejects_any_line_break():
    # cold M2 R1-9: every separator str.splitlines() honours, or a value could inject keys
    before = block()
    for sep in (" ", " ", "\x85", "\v", "\f", "\x1c", "\x1d", "\x1e", "\r"):
        r = room("state", "set", f"intent=open PR for M1{sep}lease_session: mallory", check=False)
        assert r.returncode == 1 and "single line" in r.stderr, (repr(sep), r.returncode, r.stderr)
    assert block() == before
    assert room("lease", "check").returncode == 0
    room("state", "set", "intent=tabs\tand unicode — are fine")
    assert room("state", "get", "intent").stdout.rstrip("\n") == "tabs\tand unicode — are fine"


def t_state_next_counter():
    assert room("state", "next", "counter").stdout.strip() == "1"
    assert room_b("state", "next", "counter", session="A").stdout.strip() == "2"  # same session, other machine
    assert room("state", "next", "counter").stdout.strip() == "3"  # A syncs first, so no race
    assert block()["counter"] == "3"
    r = room("state", "next", "mission", check=False)  # "M1" is not a number
    assert r.returncode == 1 and "not a number" in r.stderr, r.stderr


def t_state_commit_rejected_after_another_push():
    room("state", "sync")
    room_b("state", "sync")
    with open(playbook_path("B", "LEDGER.md"), "a") as f:
        f.write("| L-1 | cold M1 | from B | real | M2 | open |\n")
    assert "pushed" in room_b("state", "commit", "-m", "ledger: L-1", session="A").stdout  # A's other machine
    with open(playbook_path("A", "LEDGER.md"), "a") as f:
        f.write("| L-9 | cold M1 | from A | stale | M2 | open |\n")
    r = room("state", "commit", "-m", "ledger: L-9", check=False)
    assert r.returncode == 3 and "state moved: run 'state sync', re-read, re-apply" in r.stderr, (r.returncode, r.stderr)
    ledger = open(playbook_path("A", "LEDGER.md")).read()
    assert "L-1" in ledger and "L-9" not in ledger, "the worktree is reset to the remote"
    assert g("-C", sdir("A"), "status", "--porcelain").stdout == ""
    assert "L-9" not in remote_file(PET, "docs/playbook/LEDGER.md")
    assert "nothing to commit" in room("state", "commit", "-m", "noop").stdout


def t_state_commit_moved_after_a_fetch():
    # cold M2 R1-2: any fetch moves the tracking ref; a moved branch is still exit 3 with a reset worktree
    fetches = (lambda: room("lease", "check", check=False), lambda: g("-C", CHECKOUT, "fetch", "-q", "origin"))
    for fetch_with in fetches:
        room("state", "sync")
        room_b("state", "sync")
        append("B", "HANDOFF.md", "- from B")
        room_b("state", "commit", "-m", "handoff from B")
        append("A", "HANDOFF.md", "- stale from A")
        fetch_with()
        r = room("state", "commit", "-m", "stale handoff", check=False)
        assert r.returncode == 3 and "state moved: run 'state sync'" in r.stderr, (r.returncode, r.stderr)
        assert g("-C", sdir("A"), "status", "--porcelain").stdout == ""
        assert g("-C", sdir("A"), "rev-parse", "HEAD").stdout.strip() == sha(PET, "agent-room/state")
    # nothing changed here, the branch moved and was fetched: nothing to commit, not a push error
    append("B", "HANDOFF.md", "- again")
    room_b("state", "commit", "-m", "again")
    room("lease", "check", check=False)
    assert room("state", "commit", "-m", "noop").stdout.strip() == "nothing to commit"


def t_lost_ack_is_a_success():
    # cold M2 R1-11: a push that landed but reported a failure is a success, not a lost race
    room_b("state", "sync")
    append("B", "HANDOFF.md", "- landed without an ack")
    with pre_push("B", LOST_ACK):
        r = room_b("state", "commit", "-m", "lost ack", check=False)
    assert r.returncode == 0 and "pushed" in r.stdout, (r.returncode, r.stdout, r.stderr)
    assert "landed without an ack" in remote_file(PET, "docs/playbook/HANDOFF.md")
    assert g("-C", sdir("B"), "status", "--porcelain").stdout == ""
    assert room_b("state", "commit", "-m", "noop").stdout.strip() == "nothing to commit"


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


def t_broken_state_worktree_is_rebuilt():
    # cold M2 R1-12: the checkout it was added from is cloned again, leaving the worktree dangling
    work = os.path.join(tmp, "work", "pet-r")
    g("clone", "-q", PET, work)
    kw = dict(state="R", cwd=work, session="R1")
    room("state", "path", **kw)
    for args in (("state", "path"), ("lease", "check")):
        shutil.rmtree(work)
        g("clone", "-q", PET, work)
        r = room(*args, check=False, **kw)
        assert r.returncode in (0, 5) and len(r.stderr.strip().splitlines()) == 1, (args, r.returncode, r.stderr)
        assert re.fullmatch(r"\[state worktree .* was broken; moved it to .*/R\.broken-\d{8}T\d{6}Z(-\d+)? and made "
                            r"a new one\]", r.stderr.strip()), r.stderr
        assert g("-C", sdir("R"), "rev-parse", "HEAD").stdout.strip() == sha(PET, "agent-room/state")
    assert room("state", "path", **kw).stderr == "", "a healthy worktree is left alone"
    aside = [d for d in os.listdir(os.path.join(tmp, "state")) if d.startswith("R.broken-")]
    assert len(aside) == 2, aside


def t_refuses_a_dir_that_is_not_the_state_worktree():
    # cold M2 R1-13: ROOM_STATE_DIR pointing at the project checkout must not reset or clean it
    work = os.path.join(tmp, "work", "pet-x")
    g("clone", "-q", PET, work)
    g("-C", work, "checkout", "-q", "-b", "mission/M1-x", "origin/main")
    app = os.path.join(work, "app.py")
    open(app, "w").write("uncommitted mission work\n")
    main_sha = sha(PET, "main")
    for args in (("state", "sync"), ("state", "path"), ("lease", "check"), ("state", "commit", "-m", "x")):
        r = room(*args, state=None, cwd=work, ROOM_STATE_DIR=work, check=False)
        assert r.returncode == 1 and "has branch mission/M1-x checked out" in r.stderr, (args, r.stderr)
    g("-C", work, "checkout", "-q", "--detach", "origin/main")  # detached at main, run from elsewhere
    r = room("state", "sync", state=None, cwd=tmp, ROOM_STATE_DIR=work, check=False)
    assert r.returncode == 1 and "holds no agent-room/state history" in r.stderr, r.stderr
    assert open(app).read() == "uncommitted mission work\n"
    assert g("-C", work, "rev-parse", "mission/M1-x").stdout.strip() == main_sha


def t_recreated_state_branch_rebuilds_stale_worktrees():
    # cold M2 R2-2: state worktrees of a deleted and recreated agent-room/state are stale, not foreign
    repo = bare("again")
    work = os.path.join(tmp, "work", "again")
    g("clone", "-q", repo, work)
    here = dict(cwd=work, ROOM_REPO="SigorMatt/again")  # worktree mode
    away = dict(cwd=tmp, ROOM_REPO="SigorMatt/again", ROOM_STATE_REMOTE=repo)  # clone mode
    room("state", "init", session="arch", state="GA", **here)
    room("state", "init-lead", session="L1", state="GA", **here)
    room("state", "path", state="GB", **away)
    g("--git-dir", repo, "update-ref", "-d", "refs/heads/agent-room/state")  # Matthew deletes the branch
    # and the architect recreates it (dated, or within the same second it would be the very same root commit)
    room("state", "init", session="arch", state="GARCH", GIT_AUTHOR_DATE="2026-01-01T00:00:00Z",
         GIT_COMMITTER_DATE="2026-01-01T00:00:00Z", **here)
    new = sha(repo, "agent-room/state")
    for state, kw in (("GA", here), ("GB", away)):
        r = room("state", "path", state=state, **kw)
        assert r.stdout.strip() == sdir(state), r.stdout
        assert re.fullmatch(r"\[state worktree .* is stale \(no history of the recreated agent-room/state\); moved "
                            r"it to .*\.broken-\d{8}T\d{6}Z(-\d+)? and made a new one\]", r.stderr.strip()), r.stderr
        assert g("-C", sdir(state), "rev-parse", "HEAD").stdout.strip() == new
    # the project checkout itself is still refused, even at a commit that holds docs/playbook/
    os.makedirs(os.path.join(work, "docs", "playbook"))
    open(os.path.join(work, "docs", "playbook", "notes.md"), "w").write("project notes\n")
    g("-C", work, "checkout", "-q", "--detach", "origin/main")
    g("-C", work, "add", "-A")
    g("-C", work, "commit", "-qm", "project docs")
    r = room("state", "sync", state=None, ROOM_STATE_DIR=work, check=False, **here)
    assert r.returncode == 1 and "holds no agent-room/state history" in r.stderr, r.stderr
    assert os.path.exists(os.path.join(work, "docs", "playbook", "notes.md"))


def push_edit(repo, name, fn):
    """Edit a playbook file on the state branch from another clone, as a hand edit on GitHub would."""
    other = tempfile.mkdtemp(dir=tmp, prefix="edit-")
    g("clone", "-q", "--branch", "agent-room/state", repo, other)
    path = os.path.join(other, "docs", "playbook", name)
    text = fn(open(path).read())  # read before open(..., "w") truncates it
    open(path, "w").write(text)
    g("-C", other, "commit", "-qam", f"hand edit of {name}")
    g("-C", other, "push", "-q", "origin", "HEAD:agent-room/state")


AGAIN = dict(cwd=os.path.join(tmp, "work", "again"), ROOM_REPO="SigorMatt/again", state="GA")
BREAK_FENCE = ("```agent-room-state", "``` agent-room-state")


def t_unreadable_lease_does_not_block_posting():
    # cold M2 R2-3: with MISSIONS.md missing or its block broken, nobody can be shown to hold the lease
    assert "room 1 in SigorMatt/again" in room("new", "Phase 1", **AGAIN).stdout
    r = room("say", "1", "lead", "ESCALATION-1: preflight fails, need X", session="L1", **AGAIN)
    assert "sent #" in r.stdout and len(r.stderr.strip().splitlines()) == 1, (r.stdout, r.stderr)
    assert r.stderr.startswith("[lease unreadable, posting anyway: ") and "MISSIONS.md is missing" in r.stderr
    room("state", "init-lead", session="L1", **AGAIN)
    room("lease", "take", session="L1", **AGAIN)
    assert room("say", "1", "lead", "STATUS: held", session="L2", check=False, **AGAIN).returncode == 5
    push_edit(os.path.join(tmp, "git", "SigorMatt", "again.git"), "MISSIONS.md", lambda t: t.replace(*BREAK_FENCE, 1))
    for session in ("L1", "L2"):
        r = room("say", "1", "lead", f"ESCALATION-2: MISSIONS.md block broken ({session})", session=session, **AGAIN)
        assert "sent #" in r.stdout and "has no agent-room-state block" in r.stderr, (r.stdout, r.stderr)
    r = room("lease", "check", session="L1", check=False, **AGAIN)
    assert r.returncode == 1 and "has no agent-room-state block" in r.stderr, "lease check still reports it"
    transcript = room("read", "1", "--all", **AGAIN).stdout
    assert "preflight fails" in transcript and "(L1)" in transcript and "(L2)" in transcript
    assert "STATUS: held" not in transcript


def t_broken_block_can_be_repaired():
    # cold M2 R2-4: state commit of MISSIONS.md goes ahead, with a warning, while the pushed block is broken
    room("state", "sync", session="L1", **AGAIN)
    missions = playbook_path("GA", "MISSIONS.md")
    text = open(missions).read()
    assert BREAK_FENCE[1] in text and "lease_session: L1" in text, text
    open(missions, "w").write(text.replace(BREAK_FENCE[1], BREAK_FENCE[0], 1))
    r = room("state", "commit", "-m", "repair the block", session="L1", **AGAIN)
    assert "pushed" in r.stdout and len(r.stderr.strip().splitlines()) == 1, (r.stdout, r.stderr)
    assert r.stderr.startswith("[lease unreadable, committing anyway: ") and "no agent-room-state block" in r.stderr
    assert room("lease", "check", session="L1", **AGAIN).returncode == 0, "the repaired block holds L1's lease"
    room("state", "sync", session="L2", **AGAIN)
    append("GA", "LEDGER.md", "| L-1 | not L2's to write |")
    r = room("state", "commit", "-m", "ledger", session="L2", check=False, **AGAIN)
    assert r.returncode == 5 and "held by L1" in r.stderr, (r.returncode, r.stderr)


# --- lease

def t_lease_take_race():
    assert "released" in room("lease", "release").stdout  # free, so B gets as far as its push
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
    # without a race, B stands down; only --takeover wins the next generation
    r = room_b("lease", "take", check=False)
    assert r.returncode == 3 and "lease held by A: stand down" in r.stderr, (r.returncode, r.stderr)
    assert room_b("lease", "take", "--takeover").stdout.strip() == str(gen + 2)
    assert room("lease", "check", check=False).returncode == 5
    assert room_b("lease", "check", session=None, check=False).returncode == 5  # falls back to the hostname
    assert room_b("lease", "check", "--session", "B", session="X").returncode == 0  # --session wins over env
    r = room_b("lease", "check", session=None, CLAUDE_CODE_SESSION_ID="B0123456789", check=False)
    assert r.returncode == 5 and "(B0123456)" in r.stdout, r.stdout


def t_lease_take_stands_down_and_release():
    # cold M2 R1-3: a duplicate launch stands down; leads release, so the next plain take wins
    before = block()
    assert before["lease_session"] == "B"
    r = room("lease", "take", session="S1", state="S1", check=False)
    assert r.returncode == 3 and "lease held by B: stand down" in r.stderr, (r.returncode, r.stderr)
    assert block() == before, "standing down writes nothing"
    r = room("lease", "release", check=False)  # A isn't the holder
    assert r.returncode == 5 and "held by B" in r.stderr, (r.returncode, r.stderr)
    assert "released by B" in room_b("lease", "release").stdout
    assert block()["lease_session"] == "none" and block()["lease_generation"] == before["lease_generation"]
    assert room_b("lease", "check", check=False).returncode == 5
    gen = int(before["lease_generation"])
    assert room("lease", "take", session="S1", state="S1").stdout.strip() == str(gen + 1)
    r = room_b("lease", "take", session="S2", check=False)  # launched moments later
    assert r.returncode == 3 and "lease held by S1: stand down" in r.stderr, r.stderr
    assert room_b("lease", "take", "--takeover", session="S2").stdout.strip() == str(gen + 2)
    # a lease take whose push lands but loses its acknowledgement still holds the lease (cold M2 R1-11)
    room_b("lease", "release", session="S2")
    with pre_push("B", LOST_ACK):
        r = room_b("lease", "take", check=False)
    assert r.returncode == 0 and r.stdout.strip() == str(gen + 3), (r.returncode, r.stdout, r.stderr)
    assert room_b("lease", "check").returncode == 0


def t_stale_lead_cannot_write():
    # cold M2 R1-1: after a successor takes the lease, the old lead can't write lead-owned state
    room("lease", "take", "--takeover")
    room_b("lease", "take", "--takeover")
    room_b("state", "set", "step=spec")
    before = block()
    for args in (("state", "set", "step=pr", "pr=17"), ("state", "next", "counter")):
        r = room(*args, check=False)
        assert r.returncode == 5 and "held by B" in r.stderr, (args, r.returncode, r.stderr)
    room("state", "sync")
    append("A", "LEDGER.md", "| L-7 | stale lead |")
    r = room("state", "commit", "-m", "stale ledger", check=False)
    assert r.returncode == 5 and "LEDGER.md are lead-owned" in r.stderr and "held by B" in r.stderr, r.stderr
    assert block() == before and "L-7" not in remote_file(PET, "docs/playbook/LEDGER.md")
    room("state", "sync")
    append("A", "HANDOFF.md", "- architect-owned files need no lease")
    assert "pushed" in room("state", "commit", "-m", "handoff").stdout
    room_b("lease", "release")
    assert room_b("state", "set", "step=x", check=False).returncode == 5, "a released lease is no one's"


def t_renaming_a_lead_file_needs_the_lease():
    # cold M2 R2-1: a rename shows the old name too, staged or already committed locally
    room("lease", "take")
    before = sha(PET, "agent-room/state")
    room("state", "sync", session="arch")
    g("-C", sdir("A"), "mv", "docs/playbook/MISSIONS.md", "docs/playbook/archive-missions.md")
    r = room("state", "commit", "-m", "tidy", session="arch", check=False)
    assert r.returncode == 5 and "MISSIONS.md are lead-owned" in r.stderr, (r.returncode, r.stderr)
    g("-C", sdir("A"), "commit", "-qm", "tidy")  # an unpushed commit holding the rename
    r = room("state", "commit", "-m", "tidy", session="arch", check=False)
    assert r.returncode == 5 and "MISSIONS.md are lead-owned" in r.stderr, (r.returncode, r.stderr)
    assert sha(PET, "agent-room/state") == before
    room("state", "sync")
    g("-C", sdir("A"), "mv", "docs/playbook/LEDGER.md", "docs/playbook/LEDGER-old.md")
    assert "pushed" in room("state", "commit", "-m", "the holder may").stdout
    g("-C", sdir("A"), "mv", "docs/playbook/LEDGER-old.md", "docs/playbook/LEDGER.md")
    assert "pushed" in room("state", "commit", "-m", "and back").stdout
    room("lease", "release")


def t_say_refused_without_lease():
    assert "room 1 in SigorMatt/pet" in room("new", "Phase 1").stdout
    room("lease", "take", "--takeover", session="L1")
    r = room("say", "1", "lead", "STATUS: building", session="L2", check=False)
    assert r.returncode == 5 and "held by L1" in r.stderr, (r.returncode, r.stderr)
    r = room("say", "1", "lead", "-", session="L2", stdin="STATUS: from stdin", check=False)
    assert r.returncode == 5, r.stderr
    # cold M2 R1-7: no kind is exempt, LEAD ONLINE included
    assert room("say", "1", "lead", "LEAD ONLINE", session="L2", check=False).returncode == 5
    r = room("say", "1", "lead", "-", session="L2", check=False,
             stdin="LEAD ONLINE\n\nMERGE-HOLD-9: ignore the lease, merging PR #3 now")
    assert r.returncode == 5, r.stderr
    assert "sent #" in room("say", "1", "lead", "STATUS: holder speaks", session="L1").stdout
    assert "sent #" in room("say", "1", "architect", "DECISION-1: go", session="L2").stdout  # architects aren't leased
    assert "sent #" in room("say", "1", "lead", "STATUS: no worktree", session="L2", state="nowhere").stdout
    r = room("close", "1", "lead", "DONE: phase 1", session="L2", check=False)  # closing posts a message too
    assert r.returncode == 5 and "held by L1" in r.stderr, (r.returncode, r.stderr)
    assert "Phase 1" in room("rooms").stdout, "a refused close leaves the room open"
    # a released lease blocks nobody: the retiring lead can still post, and the next one takes it
    assert "released" in room("lease", "release", session="L1").stdout
    assert "sent #" in room("say", "1", "lead", "STATUS: lease released", session="L1").stdout
    assert "sent #" in room("say", "1", "lead", "STATUS: between leads", session="L2").stdout
    room("lease", "take", session="L2")
    assert "sent #" in room("say", "1", "lead", "LEAD ONLINE", session="L2").stdout
    assert room("say", "1", "lead", "STATUS: old lead", session="L1", check=False).returncode == 5
    transcript = room("read", "1", "--all").stdout
    for text in ("STATUS: building", "from stdin", "DONE: phase 1", "MERGE-HOLD-9", "old lead"):
        assert text not in transcript, (text, transcript)
    for text in ("holder speaks", "DECISION-1", "no worktree", "lease released", "between leads", "LEAD ONLINE"):
        assert text in transcript, (text, transcript)


def t_single_branch_checkout():
    # cloud checkouts fetch only main, so every state fetch must name its refspec
    single = os.path.join(tmp, "work", "pet-single")
    g("clone", "-q", "--single-branch", "--branch", "main", PET, single)
    assert g("-C", single, "config", "--get-all", "remote.origin.fetch").stdout.split() == [
        "+refs/heads/main:refs/remotes/origin/main"]
    kw = dict(state="S", cwd=single, session="S1")
    assert room("state", "path", **kw).stdout.strip() == sdir("S")
    assert os.path.isfile(os.path.join(sdir("S"), ".git")), "a worktree of the single-branch checkout"
    gen = int(room("lease", "take", "--takeover", **kw).stdout)
    room_b("state", "set", "step=from-b", session="S1")  # S1's other machine moves the branch
    assert room("state", "get", "step", **kw).stdout.strip() == "from-b"
    tracking = g("-C", single, "rev-parse", "refs/remotes/origin/agent-room/state").stdout.strip()
    assert tracking == sha(PET, "agent-room/state")
    assert room("lease", "check", **kw).returncode == 0
    assert int(room_b("lease", "take", "--takeover").stdout) == gen + 1
    r = room("lease", "check", check=False, **kw)
    assert r.returncode == 5 and "held by B" in r.stdout, r.stdout
    room("state", "sync", **kw)
    room_b("state", "set", "step=b2")
    append("S", "HANDOFF.md", "- stale")
    r = room("state", "commit", "-m", "stale", check=False, **kw)
    assert r.returncode == 3 and "state moved" in r.stderr, (r.returncode, r.stderr)
    assert room("state", "next", "counter", check=False, **kw).returncode == 5


# --- preflight

def set_pipeline(value, commit=True):
    room("state", "sync")
    text = open(playbook_path()).read()
    lines = [ln for ln in text.splitlines() if not ln.startswith("pipeline:")]
    if value:
        lines.insert(2, f"pipeline: {value}")
    open(playbook_path(), "w").write("\n".join(lines) + "\n")
    if commit:
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
    # cold M2 R1-14: an uncommitted pin in the worktree is not on the branch
    set_pipeline("v1.0.0", commit=False)
    r = room("preflight", "--role", "architect")
    expect(r, "state branch", "!")
    assert "'main'" in line(r, "state branch"), r.stdout
    os.remove(playbook_path(name="DESIGN.md"))  # nor is an uncommitted deletion
    expect(room("preflight", "--role", "architect"), "state branch", "!")
    room("state", "sync")
    set_pipeline("v1.0.0")
    r = room("preflight", "--role", "architect")
    expect(r, "state branch", "✓")
    assert "pinned to v1.0.0" in r.stdout


def t_preflight_state_branch_fails():
    # cold M2 R1-15: only `main` warns; any other non-tag fails; a missing line says how to fix it
    set_pipeline("latest")
    r = room("preflight", "--role", "architect", check=False)
    assert r.returncode == 1
    expect(r, "state branch", "✗")
    assert "'latest', not a release tag" in line(r, "state branch"), r.stdout
    set_pipeline(None)
    r = room("preflight", "--role", "architect", check=False)
    assert r.returncode == 1
    expect(r, "add `pipeline: vX.Y.Z` to PLAYBOOK.md", "✗")
    assert "state init" not in line(r, "state branch"), r.stdout
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
    for n in ("MISSIONS.md", "LEDGER.md", "QODO-VALUE.md"):  # uncommitted copies don't count (cold M2 R1-14)
        open(playbook_path("old", n), "w").write(open(os.path.join(TEMPLATES, n)).read())
    r = room("preflight", "--role", "lead", check=False, **kw)
    expect(r, "lead-owned files missing", "✗")
    room("state", "sync", **kw)
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
