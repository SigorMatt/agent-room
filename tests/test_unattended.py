#!/usr/bin/env python3
"""Tests for room.py's unattended operation: watchdog, join-line, handoff, reconcile, budget, and the
machine block's status and mission_started. Run: python3 tests/test_unattended.py

As in test_state.py and test_gate.py, the project repo is a local bare git repo standing in for GitHub;
`gh` is fake_gh_state.py (room comments go on to fake_gh.py, and commit dates come from the bare repo) and
`curl` is fake_curl.py. A stall of hours takes no waiting: commits are dated with GIT_COMMITTER_DATE, and
room comments are backdated in the fake's database.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ROOM = os.path.join(ROOT, "room.py")
TEMPLATES = os.path.join(ROOT, "templates", "playbook")
tmp = tempfile.mkdtemp(prefix="room-unattended-")
BIN = os.path.join(tmp, "bin")
HOME = os.path.join(tmp, "home")
GH_CFG = os.path.join(tmp, "gh-state.json")
DB = os.path.join(tmp, "db.json")
CURL_LOG = os.path.join(tmp, "curl.log")
CURSORS = os.path.join(tmp, "cursors")
STATE_DIR = os.path.join(tmp, "state", "A")
for d in (BIN, HOME):
    os.makedirs(d)
for name, target in (("gh", "fake_gh_state.py"), ("curl", "fake_curl.py")):
    with open(os.path.join(BIN, name), "w") as f:
        f.write(f'#!/bin/sh\nexec "{sys.executable}" "{os.path.join(HERE, target)}" "$@"\n')
    os.chmod(os.path.join(BIN, name), 0o755)

ENV = {k: v for k, v in os.environ.items()
       if not k.startswith(("ROOM_", "GIT_", "QODO_", "CLAUDE_CODE_SESSION", "FAKE_"))}
ENV.update(PATH=BIN + os.pathsep + os.environ["PATH"], HOME=HOME, XDG_CONFIG_HOME=os.path.join(HOME, ".config"),
           GIT_CONFIG_NOSYSTEM="1", FAKE_GH_DB=DB, FAKE_GH_STATE=GH_CFG, FAKE_GH_GIT_ROOT=os.path.join(tmp, "git"),
           FAKE_CURL_LOG=CURL_LOG, ROOM_REPO="SigorMatt/pet", ROOM_STATE=CURSORS, ROOM_STATE_DIR=STATE_DIR,
           ROOM_SESSION="L1", ROOM_NTFY_TOPIC="topic-secret")
GIT_ENV = dict(ENV, GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="test@example.com",
               GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="test@example.com")

PET = os.path.join(tmp, "git", "SigorMatt", "pet.git")  # /git/OWNER/NAME, like the proxy's URLs
CHECKOUT = os.path.join(tmp, "work", "pet")
MISSION_BRANCH = "mission/M1-greet"
JOIN = ("Join agent room 1 in SigorMatt/pet as lead, pipeline {v}. "
        "Follow LEAD.md: https://github.com/SigorMatt/agent-room/blob/{v}/LEAD.md")
TAKEOVER = " Take over the lease (lease take --takeover): the previous lead stopped without handing over."


def g(*args, cwd=CHECKOUT, check=True, **env):
    r = subprocess.run(["git", *args], cwd=cwd, env=dict(GIT_ENV, **env), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise AssertionError(f"git {args} failed: {r.stderr}")
    return r


def room(*args, check=False, cwd=CHECKOUT, stdin=None, **env):
    e = dict(ENV)
    for k, v in env.items():
        if v is None:
            e.pop(k, None)
        else:
            e[k] = v
    r = subprocess.run([sys.executable, ROOM, *args], env=e, cwd=cwd, input=stdin, capture_output=True,
                       text=True, timeout=120)
    if check and r.returncode != 0:
        raise AssertionError(f"{args} exited {r.returncode}:\n{r.stdout}\n{r.stderr}")
    return r


def out(r):
    return f"exit {r.returncode}\n{r.stdout}\n{r.stderr}"


def test(name, fn):
    fn()
    print(f"ok  {name}")


def iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def ago(hours):
    """(time, env) for a commit dated HOURS ago."""
    t = int(time.time() - hours * 3600)
    return t, {"GIT_COMMITTER_DATE": f"@{t} +0000", "GIT_AUTHOR_DATE": f"@{t} +0000"}


def set_state(*pairs, hours=None, **env):
    """state set as the lease holder; with HOURS, its commit is dated that many hours ago. Returns the date."""
    t, dated = ago(hours or 0)
    room("state", "set", *pairs, check=True, **(dated if hours is not None else {}), **env)
    return t


def remote_file(name, ref="agent-room/state"):
    r = g("--git-dir", PET, "show", f"{ref}:{name}", check=False)
    return r.stdout if r.returncode == 0 else None


def block(ref="agent-room/state"):
    body = remote_file("docs/playbook/MISSIONS.md", ref).split("```agent-room-state\n", 1)[1].split("```", 1)[0]
    return dict(ln.split(": ", 1) if ": " in ln else (ln.rstrip(":"), "") for ln in body.splitlines())


def state_sha():
    return g("--git-dir", PET, "rev-parse", "agent-room/state").stdout.strip()


def edit_state(name, fn, hours=None, **env):
    """Edit a playbook file in the state worktree and commit it (dated HOURS ago if given); returns the text
    before."""
    room("state", "sync", check=True, **env)
    path = os.path.join(STATE_DIR, "docs", "playbook", name)
    with open(path) as f:
        text = f.read()
    with open(path, "w") as f:
        f.write(fn(text))
    room("state", "commit", "-m", f"test: edit {name}", check=True, **(ago(hours)[1] if hours is not None else {}),
         **env)
    return text


def gh_cfg(**cfg):
    with open(GH_CFG, "w") as f:
        json.dump(cfg, f)


# --- the fake GitHub's room

def load_db():
    with open(DB) as f:
        return json.load(f)


def comments(n="1"):
    return load_db()["repos"]["SigorMatt/pet"]["issues"][n]["comments"]


def text_of(c):
    body = c["body"].split("\n\n---\n_Generated", 1)[0]
    return body.split("]**\n\n", 1)[1].strip() if "]**\n\n" in body else body.strip()


def tag(c):
    return re.match(r"<!-- agent-room role=(\S+) session=(\S+) -->", c["body"]).groups()


def backdate(pred, hours, n="1"):
    """Make the room's comments matching PRED look HOURS old."""
    db = load_db()
    stamp = iso(time.time() - hours * 3600)
    for c in db["repos"]["SigorMatt/pet"]["issues"][n]["comments"]:
        if pred(c):
            c["created_at"] = c["updated_at"] = stamp
    with open(DB, "w") as f:
        json.dump(db, f)


def alarms():
    """The trusted watchdog's messages: every one is a LEAD-SILENT."""
    return [c for c in comments() if c["user"]["login"] == "SigorMatt" and tag(c)[0] == "watchdog"]


def age_alarms(hours=10):
    """Push earlier alarms back in time, so they belong to an earlier stall."""
    backdate(lambda c: "role=watchdog" in c["body"], hours)


def buzzes():
    try:
        with open(CURL_LOG) as f:
            return [json.loads(x) for x in f if x.strip()]
    except FileNotFoundError:
        return []


def watchdog(*args, **env):
    env.setdefault("ROOM_SESSION", "wd")
    return room("watchdog", "1", *args, **env)


def push_mission(hours, branch=MISSION_BRANCH):
    """Push BRANCH to a new commit on main, committed HOURS ago. Returns its date."""
    t, dated = ago(hours)
    g("checkout", "-q", "-B", branch, "origin/main")
    with open(os.path.join(CHECKOUT, "work.txt"), "w") as f:
        f.write(f"{branch} {t} {time.time()}\n")
    g("add", "-A")
    g("commit", "-q", "-m", f"work on {branch}", **dated)
    g("push", "-q", "-f", "origin", f"HEAD:refs/heads/{branch}")
    return t


def pre_push(hook_body):
    """A pre-push hook for the state worktree; returns its directory. Unset with no_hooks()."""
    hooks = tempfile.mkdtemp(dir=tmp, prefix="hooks-")
    with open(os.path.join(hooks, "pre-push"), "w") as f:
        f.write("#!/bin/sh\ncat >/dev/null\nunset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR\n" + hook_body)
    os.chmod(os.path.join(hooks, "pre-push"), 0o755)
    g("-C", STATE_DIR, "config", "core.hooksPath", hooks)
    return hooks


def no_hooks():
    g("-C", STATE_DIR, "config", "--unset", "core.hooksPath")


def setup():
    g("init", "-q", "--bare", "--initial-branch=main", PET, cwd=tmp)
    g("clone", "-q", PET, CHECKOUT, cwd=tmp)
    room("state", "init", check=True, ROOM_SESSION="arch")
    room("state", "init-lead", check=True)
    room("lease", "take", check=True)
    assert "room 1 in SigorMatt/pet" in room("new", "Phase 1", check=True).stdout
    set_state("mission=M1", "room=1")
    g("fetch", "-q", "origin")
    gh_cfg()


# --- the machine block

def t_template_keys():
    text = open(os.path.join(TEMPLATES, "MISSIONS.md")).read()
    assert "waiting_for_owner: no\nstatus: running\nmission_started: none\n```" in text, text
    b = block()
    assert b["status"] == "running" and b["mission_started"] == "none", b
    for bad, why in (("status=sleeping", "status must be one of running, paused, stopped, done"),
                     ("mission_started=yesterday", "ISO-8601"), ("mission_started=2026-13-01T00:00:00Z", "ISO-8601")):
        r = room("state", "set", bad)
        assert r.returncode == 1 and why in r.stderr, (bad, out(r))
    set_state("mission_started=2026-11-15T08:00:00+00:00")
    set_state("mission_started=none")


# --- watchdog

def t_watchdog_stale_alarms():
    t = set_state("step=build", hours=5)
    set_state("cursor=0")  # newer state writes that don't change the step are not progress
    set_state("cursor=1")
    before, n = state_sha(), len(buzzes())
    r = watchdog()
    assert r.returncode == 0, out(r)
    assert "alarm: no progress for 5h" in r.stdout and "sent #" in r.stdout and "[buzz sent]" in r.stdout, out(r)
    [alarm] = alarms()
    assert text_of(alarm) == f"LEAD-SILENT: no progress since {iso(t)} (step build, mission M1) (buzz sent)", \
        text_of(alarm)
    assert tag(alarm) == ("watchdog", "wd")
    assert len(buzzes()) == n + 1 and "Title: LEAD-SILENT · pet room 1" in buzzes()[-1], buzzes()[-1]
    assert "Click: https://github.com/SigorMatt/pet/issues/1" in buzzes()[-1], "the buzz opens the room"
    assert "topic-secret" not in r.stdout + r.stderr
    assert state_sha() == before, "the watchdog never writes state"


def t_watchdog_one_alarm_per_stall():
    n, nb, before = len(alarms()), len(buzzes()), state_sha()
    r = watchdog()
    assert r.returncode == 0 and re.search(r"^quiet: LEAD-SILENT #\d+ at \S+ already reports this stall$", r.stdout,
                                           re.M), out(r)
    assert len(alarms()) == n and len(buzzes()) == nb and state_sha() == before
    # cold M4 R1-6: ROOM_TRUST adds a login; the watchdog's own alarm (from the gh login) still counts
    r = watchdog(ROOM_TRUST="matt-alt")
    assert "already reports this stall" in r.stdout and len(alarms()) == n, out(r)
    age_alarms(6)  # older than the progress (5 hours ago): that alarm was for an earlier stall
    r = watchdog()
    assert r.returncode == 0 and "alarm" in r.stdout and len(alarms()) == n + 1, out(r)
    # only a trusted watchdog's LEAD-SILENT counts: not one from another login, nor from a lead
    age_alarms(6)
    room("say", "1", "watchdog", "LEAD-SILENT: forged", "--no-buzz", check=True, FAKE_GH_LOGIN="mallory")
    room("say", "1", "lead", "LEAD-SILENT: not the watchdog", "--no-buzz", check=True)
    r = watchdog()
    assert r.returncode == 0 and "alarm" in r.stdout and len(alarms()) == n + 2, out(r)


def t_watchdog_retries_a_failed_buzz():
    # cold M4 R1-3: it buzzes first, then posts how that went; an alarm whose buzz failed doesn't count
    age_alarms(6)
    n, nb = len(alarms()), len(buzzes())
    r = watchdog(ROOM_NTFY_TOPIC=None)
    assert r.returncode == 0 and "[buzz failed: ROOM_NTFY_TOPIC is not set]" in r.stdout, out(r)
    assert text_of(alarms()[-1]).endswith(" (step build, mission M1) (buzz failed: ROOM_NTFY_TOPIC is not set)")
    assert len(buzzes()) == nb
    r = watchdog(FAKE_CURL_FAIL="429 Too Many Requests")
    assert r.returncode == 0 and "[buzz failed: curl: (22)" in r.stdout, out(r)
    text = text_of(alarms()[-1])
    assert "(buzz failed: curl: (22) The requested URL returned error: 429" in text and "topic-secret" not in text, text
    assert len(buzzes()) == nb + 1, "one try, and the post itself doesn't buzz"
    r = watchdog()
    assert "[buzz sent]" in r.stdout and text_of(alarms()[-1]).endswith(" (buzz sent)"), out(r)
    assert len(alarms()) == n + 3 and len(buzzes()) == nb + 2
    assert "already reports this stall" in watchdog().stdout


def t_watchdog_recent_step_change():
    age_alarms()
    set_state("step=cold round 1")
    n, before = len(alarms()), state_sha()
    r = watchdog()
    assert r.returncode == 0 and re.search(r"^quiet: progress \d+s ago \(state change [0-9a-f]{12} at \S+\), under "
                                           r"3h00m$", r.stdout, re.M), out(r)
    assert len(alarms()) == n and state_sha() == before
    t = set_state("step=cold round 2", hours=1)  # a step change written now, dated an hour ago
    r = watchdog()
    assert r.returncode == 0 and "quiet: progress 1h00m ago" in r.stdout, out(r)
    r = watchdog("--silent-after", "45m")  # drills use a short one
    assert r.returncode == 0 and "alarm: no progress for 1h" in r.stdout, out(r)
    assert text_of(alarms()[-1]) == f"LEAD-SILENT: no progress since {iso(t)} (step cold round 2, mission M1) (buzz sent)"
    for bad in ("3x", "0m", "", "h"):
        r = watchdog("--silent-after", bad)
        assert r.returncode == 2 and "duration" in r.stderr, (bad, out(r))


def t_watchdog_recent_mission_push():
    age_alarms()
    set_state("step=gate", hours=5)
    push_mission(7, "mission/M0-old")
    push_mission(0)
    n = len(alarms())
    r = watchdog()
    assert r.returncode == 0 and "quiet: progress" in r.stdout and f"({MISSION_BRANCH} pushed at" in r.stdout, out(r)
    assert len(alarms()) == n
    t = push_mission(4)  # the newest tip, committed four hours ago: progress is the later of it and the step change
    r = watchdog()
    assert r.returncode == 0 and "alarm: no progress for 4h" in r.stdout, out(r)
    assert text_of(alarms()[-1]) == f"LEAD-SILENT: no progress since {iso(t)} (step gate, mission M1) (buzz sent)"
    for branch in (MISSION_BRANCH, "mission/M0-old"):  # merged and deleted, as GitHub does
        g("push", "-q", "origin", "--delete", branch)
    g("checkout", "-q", "-B", "main", "origin/main")


def t_watchdog_progress_counts_the_merge_and_its_bookkeeping():
    # cold M4 R1-1: GitHub deletes a merged mission branch, and merge writes intent and pr but no step
    age_alarms()
    set_state("step=gate", hours=5)
    push_mission(0.1)
    assert "quiet: progress" in watchdog().stdout
    g("push", "-q", "origin", "--delete", MISSION_BRANCH)
    g("checkout", "-q", "-B", "main", "origin/main")
    merged = dict(state="closed", merged=True, merged_at=iso(time.time() - 300), merge_commit_sha="c" * 40)
    gh_cfg(pulls={"12": pull(12, MISSION_BRANCH, **merged)})
    r = watchdog()
    assert r.returncode == 0 and "quiet: progress" in r.stdout and "(PR #12 merged at" in r.stdout, out(r)
    # a merged PR from another repo's mission/* branch is no progress of this lead's
    gh_cfg(pulls={"12": dict(pull(12, MISSION_BRANCH, **merged),
                             head={"ref": MISSION_BRANCH, "sha": "d" * 40, "repo": {"full_name": "mallory/pet"}})})
    r = watchdog()
    assert "alarm: no progress for 5h" in r.stdout, out(r)
    age_alarms()
    gh_cfg()
    set_state("intent=merge PR #12 at " + "b" * 40, "pr=12")  # merge's own state write, no step change
    r = watchdog()
    assert "quiet: progress" in r.stdout and "(state change " in r.stdout, out(r)
    set_state("intent=none", "pr=none", hours=5)
    set_state("cursor=77")  # reading the room is no progress
    r = watchdog()
    assert "alarm: no progress for 5h" in r.stdout, out(r)


def t_watchdog_quiet_when_paused_stopped_or_done():
    age_alarms()
    set_state("step=build again", hours=5)
    for status in ("paused", "stopped", "done"):
        set_state(f"status={status}", hours=5)
        n, before = len(alarms()), state_sha()
        r = watchdog()
        assert r.returncode == 0 and r.stdout.strip() == f"quiet: status is {status}", out(r)
        assert len(alarms()) == n and state_sha() == before
    set_state("status=running", hours=5)
    r = watchdog()
    assert r.returncode == 0 and "alarm" in r.stdout, out(r)


def t_pause_flow():
    # state set status=paused, post PAUSED (it buzzes), release the lease; the next lead's plain take wins
    age_alarms()
    set_state("status=paused")
    r = room("say", "1", "lead", "PAUSED: at a safe point after the build step", check=True)
    assert "[buzz sent]" in r.stdout, out(r)
    assert "released by L1" in room("lease", "release", check=True).stdout
    assert block()["lease_session"] == "none" and block()["status"] == "paused"
    assert watchdog().stdout.strip() == "quiet: status is paused"
    gen = int(block()["lease_generation"])
    # cold M4 R1-2: the next lead's plain take sets status back to running, in the same write
    before = state_sha()
    assert room("lease", "take", check=True, ROOM_SESSION="L2").stdout.strip() == str(gen + 1)
    b, prev = block(), block("agent-room/state~1")
    assert b["status"] == "running" and b["lease_session"] == "L2" and prev["status"] == "paused", (b, prev)
    assert g("--git-dir", PET, "rev-parse", "agent-room/state~1").stdout.strip() == before, "one write"
    # so does a takeover, and a block without the key gains it
    set_state("status=done", ROOM_SESSION="L2")
    edit_state("MISSIONS.md", lambda t: t.replace("status: done\n", "", 1), ROOM_SESSION="L2")
    assert "status" not in block()
    room("lease", "take", "--takeover", check=True)
    assert block()["status"] == "running" and block()["lease_session"] == "L1"


def t_watchdog_status_values():
    # cold M4 R1-8: only paused, stopped or done keep it quiet, in any case; any other value counts as running
    age_alarms()
    set_state("step=build 4", hours=6)
    for value in ("Running", "runing", "active"):
        edit_state("MISSIONS.md", lambda t, v=value: re.sub(r"^status: .*$", f"status: {v}", t, count=1, flags=re.M),
                   hours=5)
        assert block()["status"] == value
        r = watchdog()
        assert r.returncode == 0 and "alarm" in r.stdout, (value, out(r))
        age_alarms()
    for value in ("PAUSED", "Stopped", "done"):
        edit_state("MISSIONS.md", lambda t, v=value: re.sub(r"^status: .*$", f"status: {v}", t, count=1, flags=re.M),
                   hours=5)
        n = len(alarms())
        r = watchdog()
        assert r.returncode == 0 and r.stdout.strip() == f"quiet: status is {value}", (value, out(r))
        assert len(alarms()) == n
    set_state("status=running", hours=5)


def t_watchdog_quiet_while_waiting_for_owner():
    age_alarms()
    set_state("step=waiting for owner", hours=5)
    n, before = len(alarms()), state_sha()
    r = watchdog()
    assert r.returncode == 0 and r.stdout.strip() == "quiet: step is waiting for owner", out(r)
    assert len(alarms()) == n and state_sha() == before
    # cold M4 R1-9: a step that starts with it, and the block's own waiting_for_owner key, are quiet too
    set_state("step=Waiting for owner (MERGE-HOLD-4)", hours=5)
    r = watchdog()
    assert r.stdout.strip() == "quiet: step is Waiting for owner (MERGE-HOLD-4)", out(r)
    for value in ("yes", "YES"):
        set_state("step=gate", f"waiting_for_owner={value}", hours=5)
        r = watchdog()
        assert r.stdout.strip() == "quiet: waiting_for_owner is yes", out(r)
    assert len(alarms()) == n
    set_state("waiting_for_owner=no", hours=5)
    r = watchdog()
    assert "alarm" in r.stdout and len(alarms()) == n + 1, out(r)


def t_watchdog_quiet_for_another_room():
    # cold M4 R1-10: a watchdog left over from an earlier phase stays quiet, and says why
    age_alarms()
    assert "room 2 in SigorMatt/pet" in room("new", "Phase 2", check=True).stdout
    set_state("room=2", "step=spec 2", hours=5)
    n = len(alarms())
    r = watchdog()
    assert r.returncode == 0 and r.stdout.strip() == ("quiet: room 1 is not the current room (MISSIONS.md records "
                                                      "room 2); this watchdog is left from an earlier phase: delete "
                                                      "it"), out(r)
    r = room("watchdog", "2", ROOM_SESSION="wd")
    assert r.returncode == 0 and "alarm" in r.stdout and "LEAD-SILENT" in text_of(comments("2")[-1]), out(r)
    assert len(alarms()) == n
    # with no room in the block, PLAYBOOK.md's decides
    set_state("room=0", hours=5)
    original = edit_state("PLAYBOOK.md", lambda t: re.sub(r"^room: .*$", "room: 2", t, count=1, flags=re.M), hours=5)
    r = watchdog()
    assert "quiet: room 1 is not the current room (PLAYBOOK.md records room 2)" in r.stdout, out(r)
    edit_state("PLAYBOOK.md", lambda t: original, hours=5)
    set_state("room=1", hours=5)


def t_watchdog_missing_status_reads_running():
    age_alarms()
    set_state("step=build 3", hours=5)
    edit_state("MISSIONS.md", lambda t: t.replace("status: running\n", "", 1), hours=5)
    assert "status" not in block()
    r = watchdog()
    assert r.returncode == 0 and "alarm" in r.stdout, out(r)
    set_state("status=running")


def t_watchdog_without_a_checkout():
    # the watchdog's scheduled session may start anywhere: a shallow clone of the state branch is deepened
    age_alarms()
    t = set_state("step=spec", hours=5)
    for i in range(3):
        set_state(f"cursor={i + 10}")
    kw = dict(cwd=tmp, ROOM_STATE_DIR=os.path.join(tmp, "state", "W"), ROOM_STATE_REMOTE=f"file://{PET}")
    room("state", "path", check=True, **kw)
    wdir = kw["ROOM_STATE_DIR"]
    assert g("-C", wdir, "rev-parse", "--is-shallow-repository").stdout.strip() == "true"
    assert g("-C", wdir, "rev-list", "--count", "HEAD").stdout.strip() == "1"
    before = state_sha()
    r = watchdog(**kw)
    assert r.returncode == 0 and "alarm" in r.stdout, out(r)
    assert text_of(alarms()[-1]) == f"LEAD-SILENT: no progress since {iso(t)} (step spec, mission M1) (buzz sent)"
    assert state_sha() == before
    r = watchdog(**kw)
    assert "already reports this stall" in r.stdout, out(r)


# --- join-line

def t_join_line():
    r = room("join-line", "1", check=True)
    assert r.stdout.strip() == JOIN.format(v="main"), out(r)
    r = room("join-line", "1", "--takeover", check=True)
    assert r.stdout.strip() == JOIN.format(v="main") + TAKEOVER, out(r)
    r = room("join-line", "1", check=True, cwd=tmp, ROOM_STATE_DIR=os.path.join(tmp, "state", "J"),
             ROOM_STATE_REMOTE=PET)
    assert r.stdout.strip() == JOIN.format(v="main"), out(r)
    # v1.md: links name the pinned tag, so a pin bumped mid-mission reaches the next lead
    original = edit_state("PLAYBOOK.md", lambda t: re.sub(r"^pipeline: .*$", "pipeline: v1.0.1", t, count=1, flags=re.M))
    try:
        assert room("join-line", "1", check=True).stdout.strip() == JOIN.format(v="v1.0.1")
    finally:
        edit_state("PLAYBOOK.md", lambda t: original)


# --- handoff

def t_handoff_refused():
    set_state("mission=M2", "step=gate")
    before, n = state_sha(), len(comments())
    last = str(comments()[-1]["id"])
    r = room("handoff", "1", "--step", "spec", "--cursor", last, ROOM_SESSION="L9")
    assert r.returncode == 5 and "not handed off" in r.stderr and "held by L1" in r.stderr, out(r)
    assert state_sha() == before and len(comments()) == n, "nothing posted, nothing written"
    # local work in the state worktree would stop the state write after posting, so it stops the post
    with open(os.path.join(STATE_DIR, "docs", "playbook", "LEDGER.md"), "a") as f:
        f.write("| L-5 | draft |\n")
    r = room("handoff", "1", "--step", "spec", "--cursor", last)
    assert r.returncode == 1 and "uncommitted changes" in r.stderr, out(r)
    assert state_sha() == before and len(comments()) == n
    room("state", "sync", check=True)
    r = room("handoff", "1", "--step", "spec\nlease_session: mallory", "--cursor", last)
    assert r.returncode == 1 and "single line" in r.stderr and len(comments()) == n, out(r)
    # cold M4 R1-5: the lead names the last comment it acted on: required, and a comment of this room
    for args, code, why in ((("--step", "spec"), 2, "--cursor"), (("--step", "spec", "--cursor", "abc"), 2, "--cursor"),
                            (("--step", "spec", "--cursor", "999999"), 1, "--cursor 999999"),
                            (("--step", "spec", "--cursor", str(comments("2")[-1]["id"])), 1, "not a comment of room 1")):
        r = room("handoff", "1", *args)
        assert r.returncode == code and why in r.stderr, (args, out(r))
    assert state_sha() == before and len(comments()) == n


def t_handoff():
    set_state("intent=merge PR #12 at " + "a" * 40)
    room("say", "1", "architect", "DECISION-9: go on", check=True, ROOM_SESSION="arch")
    assert "DECISION-9" in room("read", "1", "lead", check=True).stdout
    cursor = room("cursor", "1", "lead", check=True).stdout.strip()  # the last comment the lead acted on
    room("say", "1", "architect", "CHANGE-8: rename the greeting, from the next mission", check=True,
         ROOM_SESSION="arch")
    # cold M4 R1-5: the waiter reads CHANGE-8, moving the cursor file, but the lead hands over before acting on it
    w = room("wait", "1", "lead", "--timeout", "10", "--interval", "0.2")
    assert w.returncode == 0 and "CHANGE-8" in w.stdout, out(w)
    assert room("cursor", "1", "lead", check=True).stdout.strip() != cursor
    gen = block()["lease_generation"]
    snap = os.path.join(tmp, "room-at-push.json")
    pre_push(f'cp "$FAKE_GH_DB" "{snap}"\nexit 0\n')
    try:
        r = room("handoff", "1", "--step", "spec", "--cursor", cursor)
    finally:
        no_hooks()
    assert r.returncode == 0, out(r)
    lines = r.stdout.strip().splitlines()
    assert lines[0].startswith("sent #") and lines[-1] == JOIN.format(v="main"), out(r)
    assert "NEXT-LEAD-NEEDED" in r.stdout and "[buzz" not in r.stdout, "HANDOFF names the fallback and doesn't buzz"
    h = comments()[-1]
    assert tag(h) == ("lead", "L1") and text_of(h).splitlines()[0] == "HANDOFF: mission M2, next step spec", h
    # posted while the lease was held: the room already had it when the state write was pushed
    with open(snap) as f:
        at_push = json.load(f)["repos"]["SigorMatt/pet"]["issues"]["1"]["comments"]
    assert h["id"] in [c["id"] for c in at_push]
    b, prev = block(), block("agent-room/state~1")
    assert b["step"] == "spec" and b["cursor"] == cursor and b["intent"] == "none", b
    assert b["lease_session"] == "none" and b["lease_generation"] == gen, b
    # one state write: the commit before it is the lease still held, and only these keys changed
    assert prev["lease_session"] == "L1" and prev["step"] == "gate", prev
    assert {k for k in b if b[k] != prev.get(k)} == {"step", "cursor", "intent", "lease_session"}
    assert "handoff" in g("--git-dir", PET, "log", "-1", "--format=%s", "agent-room/state").stdout


def t_successor_takes_the_lease():
    # a released lease doesn't block the fallback post, which buzzes
    r = room("say", "1", "lead", "NEXT-LEAD-NEEDED: the successor couldn't be scheduled", check=True)
    assert "[buzz sent]" in r.stdout, out(r)
    gen, cursor = int(block()["lease_generation"]), block()["cursor"]
    l2 = dict(ROOM_SESSION="L2", ROOM_STATE=os.path.join(tmp, "cursors-L2"))
    assert room("lease", "take", check=True, **l2).stdout.strip() == str(gen + 1)
    r = room("lease", "take", ROOM_SESSION="L3")  # a duplicate launch stands down
    assert r.returncode == 3 and "stand down" in r.stderr, out(r)
    # the successor reads from the recorded cursor: what the old lead hadn't processed, and the HANDOFF
    r = room("read", "1", "lead", "--from", cursor, check=True, **l2)
    assert "CHANGE-8" in r.stdout and "HANDOFF: mission M2, next step spec" in r.stdout, out(r)
    assert "DECISION-9" not in r.stdout
    room("say", "1", "lead", "LEAD ONLINE", check=True, **l2)
    room("lease", "release", check=True, **l2)
    room("lease", "take", check=True)  # back to L1 for the tests that follow


def t_handoff_retries_when_the_branch_moves():
    set_state("step=build")
    bdir = os.path.join(tmp, "state", "B")
    b_env = f'ROOM_SESSION=arch ROOM_STATE_DIR="{bdir}" ROOM_STATE_REMOTE="{PET}"'
    room("state", "path", check=True, cwd=tmp, ROOM_STATE_DIR=bdir, ROOM_STATE_REMOTE=PET, ROOM_SESSION="arch")
    hooks = pre_push(f"""[ -e "$0.fired" ] && exit 0
touch "$0.fired"
cd "{tmp}"
{b_env} "{sys.executable}" "{ROOM}" state sync >/dev/null 2>&1
echo "- the architect wrote meanwhile" >> "{bdir}/docs/playbook/HANDOFF.md"
{b_env} "{sys.executable}" "{ROOM}" state commit -m "architect: handoff note" >/dev/null 2>&1
exit 0
""")
    n = len(comments())
    try:
        r = room("handoff", "1", "--step", "cold round 1", "--cursor", str(comments()[-1]["id"]))
    finally:
        no_hooks()
    assert os.path.exists(os.path.join(hooks, "pre-push.fired")), "the race hook did not run"
    assert r.returncode == 0, out(r)
    assert len(comments()) == n + 1, "HANDOFF is posted once"
    b = block()
    assert b["step"] == "cold round 1" and b["lease_session"] == "none", b
    assert "the architect wrote meanwhile" in remote_file("docs/playbook/HANDOFF.md")
    room("lease", "take", check=True)


# --- reconcile

def reconcile(n="1", **env):
    """reconcile, checking that it changed nothing: no state write, no cursor move."""
    path = os.path.join(CURSORS, "SigorMatt__pet", f"{n}-lead.json")
    cursor = open(path).read() if os.path.exists(path) else None
    before = state_sha()
    r = room("reconcile", n, **env)
    assert r.returncode == 0, out(r)
    assert state_sha() == before, "reconcile writes no state"
    assert (open(path).read() if os.path.exists(path) else None) == cursor, "reconcile moves no cursor"
    return r


def hint(r):
    lines = [ln for ln in r.stdout.splitlines() if re.match(r"intent (done|not done|unknown):", ln)]
    assert len(lines) == 1, out(r)
    return lines[0]


def t_reconcile_state_and_room():
    set_state("pr=none")
    r = reconcile()
    assert "recorded state (docs/playbook/MISSIONS.md on agent-room/state at " in r.stdout, out(r)
    for key in ("lease_session: L1", "step: cold round 1", "mission: M2", "status: running", "mission_started: none",
                "intent: none"):
        assert f"\n  {key}\n" in r.stdout, (key, out(r))
    assert "\nPR: none recorded\n" in r.stdout and "\ncounter 0: no escalation or hold yet\n" in r.stdout, out(r)
    handoff = [c for c in comments() if text_of(c).startswith("HANDOFF:")][-1]
    assert re.search(rf"^HANDOFF: #{handoff['id']} at \S+ from lead · L1: HANDOFF: mission M2, next step cold round 1 "
                     r"\(names the recorded step\)$", r.stdout, re.M), out(r)
    assert "\nintent: none\n" in r.stdout and not re.search(r"^intent (done|not done|unknown)", r.stdout, re.M)
    assert not re.search(r"^(status|drill):", r.stdout, re.M), out(r)
    room("say", "1", "lead", "LEAD ONLINE", check=True)
    online = comments()[-1]["id"]
    assert f"(names the recorded step; LEAD ONLINE #{online} came after it)" in reconcile().stdout
    r = reconcile(cwd=tmp, ROOM_STATE_DIR=os.path.join(tmp, "state", "R"), ROOM_STATE_REMOTE=PET)
    assert "\n  step: cold round 1\n" in r.stdout and "\nPR: none recorded\n" in r.stdout, out(r)


def pull(n, ref, state="open", merged=False, sha="b" * 40, repo="SigorMatt/pet", author="SigorMatt", **extra):
    return dict({"number": n, "state": state, "merged": merged, "base": {"ref": "main"}, "user": {"login": author},
                 "head": {"ref": ref, "sha": sha, "repo": {"full_name": repo}}}, **extra)


def t_reconcile_merge_intent():
    head, merge = "b" * 40, "c" * 40
    gh_cfg(pulls={"12": pull(12, "mission/M2-unattended")})
    set_state("pr=12", f"intent=merge PR #12 at {head}")
    r = reconcile()
    assert f"\nPR: #12 open at {head}\n" in r.stdout, out(r)
    assert hint(r) == f"intent not done: redo it (PR #12 is open at {head}; run the gate, then merge)", out(r)
    gh_cfg(pulls={"12": pull(12, "mission/M2-unattended", state="closed", merged=True, merge_commit_sha=merge)})
    r = reconcile()
    assert f"\nPR: #12 merged as {merge}\n" in r.stdout, out(r)
    assert hint(r).startswith(f"intent done: clear it (PR #12 is merged as {merge}"), out(r)
    set_state("pr=merged:12")  # as merge records it
    assert f"\nPR: #12 merged as {merge}\n" in reconcile().stdout
    gh_cfg(pulls={"12": pull(12, "mission/M2-unattended", state="closed")})
    r = reconcile()
    assert "\nPR: #12 closed without merging\n" in r.stdout, out(r)
    # cold M4 R1-11: a closed PR can't be merged, so "redo it" would be wrong
    assert hint(r) == ("intent not done: PR #12 was closed without merging, so it can't be merged: clear the "
                       "intent, and reopen the PR or escalate"), out(r)
    # cold M4 R1-4: a PR from another repo, or by an untrusted author, isn't the lead's
    for kw, why in ((dict(repo="mallory/pet", author="mallory"), "its head is in mallory/pet, not SigorMatt/pet"),
                    (dict(author="mallory"), "its author mallory is not trusted")):
        gh_cfg(pulls={"12": pull(12, "mission/M2-unattended", state="closed", merged=True, merge_commit_sha=merge,
                                 **kw)})
        r = reconcile()
        assert f"\nPR: #12 ignored: {why}\n" in r.stdout, out(r)
        assert hint(r) == f"intent unknown: PR #12 doesn't count ({why}); check it by hand", out(r)


def t_reconcile_open_pr_intent():
    gh_cfg(pulls={"20": pull(20, "mission/M20-other")})
    set_state("pr=none", "intent=open PR mission/M2-unattended")
    assert hint(reconcile()) == "intent not done: redo it (no PR from mission/M2-unattended)"
    set_state("intent=open PR for M2")
    assert hint(reconcile()) == "intent not done: redo it (no PR from M2)", "M2 is not M20"
    gh_cfg(pulls={"20": pull(20, "mission/M20-other"), "13": pull(13, "mission/M2-unattended")})
    r = reconcile()
    assert hint(r).startswith("intent done: clear it (PR #13 from mission/M2-unattended is open at"), out(r)
    set_state("intent=open PR mission/M2-unattended")
    assert hint(reconcile()).startswith("intent done: clear it (PR #13 ")
    # cold M4 R1-4: an outsider's PR from a fork branch of the same name doesn't count, in either form
    fork = pull(40, "mission/M2-unattended", repo="mallory/pet", author="mallory", sha="d" * 40)
    gh_cfg(pulls={"40": fork, "41": pull(41, "mission/M2-unattended", author="mallory")})
    for intent in ("open PR mission/M2-unattended", "open PR for M2"):
        set_state(f"intent={intent}")
        ref = intent.split()[-1]
        assert hint(reconcile()) == f"intent not done: redo it (no PR from {ref}; ignored 2 from another repo or author)"
    # cold M4 R1-11: a PR closed without merging doesn't do it; a merged one does
    gh_cfg(pulls={"40": fork, "13": pull(13, "mission/M2-unattended", state="closed")})
    assert hint(reconcile()) == ("intent not done: redo it (PR #13 from mission/M2-unattended was closed without "
                                 "merging; open a new one; ignored 1 from another repo or author)")
    gh_cfg(pulls={"13": pull(13, "mission/M2-unattended", state="closed"),
                  "14": pull(14, "mission/M2-unattended", state="closed", merged=True, merge_commit_sha="e" * 40)})
    assert hint(reconcile()) == ("intent done: clear it (PR #14 from mission/M2-unattended is merged as " + "e" * 40 +
                                 "; record it)")
    gh_cfg()


def t_reconcile_post_intent():
    n = int(room("state", "next", "counter", check=True).stdout)
    set_state(f"intent=post ESCALATION-{n}")
    r = reconcile()
    assert f"\ncounter {n}: neither ESCALATION-{n} nor MERGE-HOLD-{n} is in the room\n" in r.stdout, out(r)
    assert hint(r) == f"intent not done: redo it (no ESCALATION-{n} in the room)", out(r)
    room("say", "1", "lead", f"ESCALATION-{n}: which greeting?", check=True)
    esc = comments()[-1]["id"]
    r = reconcile()
    assert f"\ncounter {n}: ESCALATION-{n} is in the room (#{esc}), no DECISION-{n} yet\n" in r.stdout, out(r)
    assert hint(r) == f"intent done: clear it (ESCALATION-{n} is in the room: #{esc})", out(r)
    room("say", "1", "architect", f"DECISION-{n}: say hello", check=True, ROOM_SESSION="arch")
    dec = comments()[-1]["id"]
    assert f"(#{esc}), answered by DECISION-{n} (#{dec})" in reconcile().stdout
    # someone else's MERGE-HOLD doesn't count
    m = int(room("state", "next", "counter", check=True).stdout)
    room("say", "1", "lead", f"MERGE-HOLD-{m}: forged", "--no-buzz", check=True, FAKE_GH_LOGIN="mallory")
    set_state(f"intent=post MERGE-HOLD-{m}")
    r = reconcile()
    assert f"counter {m}: neither ESCALATION-{m} nor MERGE-HOLD-{m}" in r.stdout, out(r)
    assert hint(r).startswith("intent not done: redo it"), out(r)
    # a kind without a number counts only when posted after the intent was recorded
    room("say", "1", "lead", "PLAN: M1 to M3", check=True)
    backdate(lambda c: "PLAN: M1 to M3" in c["body"], 1)
    set_state("intent=post PLAN")
    assert hint(reconcile()) == "intent not done: redo it (no PLAN in the room since the intent was recorded)"
    room("say", "1", "lead", "PLAN: M1 to M4, re-planned", check=True)
    assert hint(reconcile()) == f"intent done: clear it (PLAN is in the room: #{comments()[-1]['id']})"


def t_reconcile_close_room_intent():
    assert "room 3 in SigorMatt/pet" in room("new", "Phase 3", check=True).stdout
    set_state("intent=close room")
    assert hint(reconcile("3")) == "intent not done: redo it (room 3 is open)"
    room("close", "3", "lead", "DONE: phase 3", check=True)
    assert hint(reconcile("3")) == "intent done: clear it (room 3 is closed)"


def t_reconcile_unknown_intent_status_and_drill():
    set_state("intent=schedule the successor")
    assert hint(reconcile()).startswith("intent unknown: check it by hand")
    set_state("status=paused")
    assert re.search(r"^status: paused: lease take sets it back to running", reconcile().stdout, re.M)
    original = edit_state("PLAYBOOK.md", lambda t: t.replace("test: <command>\n", "test: <command>\ndrill: stop-after-merge\n"))
    try:
        assert "\ndrill: stop-after-merge\n" in reconcile().stdout
    finally:
        edit_state("PLAYBOOK.md", lambda t: original)
    set_state("status=running", "intent=none")


# --- budget

def t_budget():
    r = room("budget")
    assert r.returncode == 1 and "mission_started is none (mission M2)" in r.stdout, out(r)
    set_state(f"mission_started={iso(time.time() - 2 * 3600)}")
    r = room("budget")
    assert r.returncode == 0 and re.search(r"^budget: mission M2 started \S+, 2h0\dm elapsed of 8h \(phase 1 in "
                                           r"PLAYBOOK\.md\): 5h5\dm left$", r.stdout, re.M), out(r)
    set_state(f"mission_started={iso(time.time() - 9 * 3600)}")
    r = room("budget")
    assert r.returncode == 6 and "elapsed of 8h (phase 1 in PLAYBOOK.md): over by 1h0" in r.stdout, out(r)
    assert "ESCALATION" in r.stdout
    # the phase's own budget, and the default for a phase PLAYBOOK.md doesn't list
    original = edit_state("PLAYBOOK.md", lambda t: t.replace("Mission budget: 8 hours.", "Mission budget: 10 hours."))
    try:
        r = room("budget")
        assert r.returncode == 0 and "elapsed of 10h (phase 1 in PLAYBOOK.md)" in r.stdout, out(r)
        set_state("phase=2")
        r = room("budget", cwd=tmp, ROOM_STATE_DIR=os.path.join(tmp, "state", "R"), ROOM_STATE_REMOTE=PET)
        assert r.returncode == 6 and "elapsed of 8h (the default): over by" in r.stdout, out(r)
    finally:
        edit_state("PLAYBOOK.md", lambda t: original)
        set_state("phase=1")


setup()
for name, fn in list(globals().items()):
    if name.startswith("t_"):
        test(name[2:], fn)
shutil.rmtree(tmp, ignore_errors=True)
print("all passed")
