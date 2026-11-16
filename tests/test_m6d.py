#!/usr/bin/env python3
"""Tests for M6d (docs/design/m6d-watchdog.md): one watchdog start per stall (B-5), and reminders while a room waits
on Matthew, with the state-unreadable reminder's retry (B-6). Run: python3 tests/test_m6d.py

As in test_relay.py, the project repo is a local bare git repo standing in for GitHub; `gh` is fake_gh_state.py
(room comments go on to fake_gh.py) and `curl` is fake_curl.py, which answers the lead task's fire endpoint and logs
each request to FAKE_FIRE_LOG. Everything runs offline; stalls are backdated, not waited for.
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
tmp = tempfile.mkdtemp(prefix="room-m6d-")
BIN = os.path.join(tmp, "bin")
HOME = os.path.join(tmp, "home")
GH_CFG = os.path.join(tmp, "gh-state.json")
DB = os.path.join(tmp, "db.json")
CURL_LOG = os.path.join(tmp, "curl.log")
FIRE_LOG = os.path.join(tmp, "fire.log")
STATE_DIR = os.path.join(tmp, "state", "A")
for d in (BIN, HOME):
    os.makedirs(d)
for name, target in (("gh", "fake_gh_state.py"), ("curl", "fake_curl.py")):
    with open(os.path.join(BIN, name), "w") as f:
        f.write(f'#!/bin/sh\nexec "{sys.executable}" "{os.path.join(HERE, target)}" "$@"\n')
    os.chmod(os.path.join(BIN, name), 0o755)

TOKEN = "sk-fire-PET-0123456789abcdef"
TASK = "trig_01AbCdEf23"
ENV = {k: v for k, v in os.environ.items()
       if not k.startswith(("ROOM_", "GIT_", "QODO_", "CLAUDE_CODE_SESSION", "FAKE_"))}
ENV.update(PATH=BIN + os.pathsep + os.environ["PATH"], HOME=HOME, XDG_CONFIG_HOME=os.path.join(HOME, ".config"),
           GIT_CONFIG_NOSYSTEM="1", FAKE_GH_DB=DB, FAKE_GH_STATE=GH_CFG, FAKE_GH_GIT_ROOT=os.path.join(tmp, "git"),
           FAKE_CURL_LOG=CURL_LOG, FAKE_FIRE_LOG=FIRE_LOG, ROOM_REPO="SigorMatt/pet",
           ROOM_STATE=os.path.join(tmp, "cursors"), ROOM_STATE_DIR=STATE_DIR, ROOM_SESSION="L1",
           ROOM_NTFY_TOPIC="topic-secret", ROOM_FIRE_TOKEN_PET=TOKEN)
GIT_ENV = dict(ENV, GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="test@example.com",
               GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="test@example.com")
PET = os.path.join(tmp, "git", "SigorMatt", "pet.git")
CHECKOUT = os.path.join(tmp, "work", "pet")
JOIN = ("Join agent room {n} in SigorMatt/pet as lead, pipeline main. "
        "Follow LEAD.md: https://github.com/SigorMatt/agent-room/blob/main/LEAD.md")
TAKEOVER = " Take over the lease (lease take --takeover): the previous lead stopped without handing over."


def g(*args, cwd=CHECKOUT, check=True, **env):
    r = subprocess.run(["git", *args], cwd=cwd, env=dict(GIT_ENV, **env), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise AssertionError(f"git {args} failed: {r.stderr}")
    return r


def room(*args, check=False, cwd=CHECKOUT, **env):
    e = dict(ENV)
    for k, v in env.items():
        if v is None:
            e.pop(k, None)
        else:
            e[k] = v
    r = subprocess.run([sys.executable, ROOM, *args], env=e, cwd=cwd, capture_output=True, text=True, timeout=120)
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
    t = int(time.time() - hours * 3600)
    return t, {"GIT_COMMITTER_DATE": f"@{t} +0000", "GIT_AUTHOR_DATE": f"@{t} +0000"}


def set_state(*pairs, hours=None, **env):
    """state set as the lease holder (L1 unless ROOM_SESSION says otherwise); with HOURS, dated that long ago."""
    t, dated = ago(hours or 0)
    room("state", "set", *pairs, check=True, **(dated if hours is not None else {}), **env)
    return t


def edit_state(name, fn):
    room("state", "sync", check=True)
    path = os.path.join(STATE_DIR, "docs", "playbook", name)
    with open(path) as f:
        text = f.read()
    with open(path, "w") as f:
        f.write(fn(text))
    room("state", "commit", "-m", f"test: edit {name}", check=True)
    return text


def load_db():
    with open(DB) as f:
        return json.load(f)


def comments(n="1"):
    return load_db()["repos"]["SigorMatt/pet"]["issues"][n]["comments"]


def text_of(c):
    body = c["body"].split("\n\n---\n_Generated", 1)[0]
    return body.split("]**\n\n", 1)[1].strip() if "]**\n\n" in body else body.strip()


def kind_of(c):
    m = re.match(r"[A-Z][A-Z-]*(?: ONLINE)?", text_of(c))
    return m.group(0) if m else None


def backdate(pred, minutes, n="1"):
    db = load_db()
    stamp = iso(time.time() - minutes * 60)
    for c in db["repos"]["SigorMatt/pet"]["issues"][n]["comments"]:
        if pred(c):
            c["created_at"] = c["updated_at"] = stamp
    with open(DB, "w") as f:
        json.dump(db, f)


def age_room(n="1", minutes=1500):
    """Push every message of room N back (25 hours by default), so it belongs to no stall a test makes next."""
    backdate(lambda c: True, minutes, n)


def opened(n, hours):
    db = load_db()
    db["repos"]["SigorMatt/pet"]["issues"][n]["created_at"] = iso(time.time() - hours * 3600)
    with open(DB, "w") as f:
        json.dump(db, f)


def set_issue_state(n, state):
    subprocess.run([os.path.join(BIN, "gh"), "api", "-X", "PATCH", f"repos/SigorMatt/pet/issues/{n}", "--input", "-"],
                   input=json.dumps({"state": state}), env=ENV, capture_output=True, text=True, check=True)


def fires():
    try:
        with open(FIRE_LOG) as f:
            return [json.loads(x) for x in f if x.strip()]
    except FileNotFoundError:
        return []


def body_of(entry):
    argv = entry["argv"]
    return json.loads(argv[argv.index("--data-raw") + 1])["text"]


def watchdog(*args, n="1", **env):
    """room.py watchdog N, checking that one run never fires more than once (M6d, B-5)."""
    env.setdefault("ROOM_SESSION", "wd")
    nf = len(fires())
    r = room("watchdog", n, *args, **env)
    assert len(fires()) - nf <= 1, f"one run fired {len(fires()) - nf} times:\n{out(r)}"
    return r


def say(text, role="lead", **env):
    room("say", "1", role, text, "--no-buzz", check=True, **env)
    return comments()[-1]["id"]


def stall(step, hours=5):
    """A fresh stall: the room aged, L1 holding the lease, and STEP recorded HOURS ago. Returns its time."""
    age_room()
    room("lease", "take", "--takeover", check=True)
    return set_state(f"step={step}", hours=hours)


def new_kinds(n, room_n="1"):
    return [kind_of(c) for c in comments(room_n)[n:]]


def setup():
    g("init", "-q", "--bare", "--initial-branch=main", PET, cwd=tmp)
    g("clone", "-q", PET, CHECKOUT, cwd=tmp)
    room("state", "init", check=True, ROOM_SESSION="arch")
    room("state", "init-lead", check=True)
    room("lease", "take", check=True)
    assert "room 1 in SigorMatt/pet" in room("new", "Phase 1", check=True).stdout
    say("LEAD ONLINE")
    set_state("mission=M1", "room=1")
    edit_state("PLAYBOOK.md", lambda t: re.sub(r"^(room:.*\n)", rf"\g<1>lead-task: {TASK}\n", t, count=1, flags=re.M))
    g("fetch", "-q", "origin")
    with open(GH_CFG, "w") as f:
        json.dump({}, f)


# --- B-5: one start per stall

def t_a_takeover_after_the_alarm_with_the_lease_held():
    stall("build 1")
    nf, n = len(fires()), len(comments())
    r = watchdog()
    assert r.returncode == 0 and "alarm: no progress for 5h" in r.stdout and "started: https://claude.ai/code/" in \
        r.stdout, out(r)
    assert r.stdout.index("alarm: ") < r.stdout.index("started: "), "the alarm comes before the fire"
    assert new_kinds(n) == ["LEAD-SILENT", "LEAD-STARTED"], new_kinds(n)
    assert text_of(comments()[-1]).endswith("(takeover join line, started by watchdog)")
    assert [body_of(x) for x in fires()[nf:]] == [JOIN.format(n=1) + TAKEOVER]
    # the same stall: no second start, after the watchdog's own
    r = watchdog()
    assert "already reports this stall" in r.stdout and "is this stall's start" in r.stdout, out(r)
    assert len(fires()) == nf + 1 and len(comments()) == n + 2


def t_a_plain_start_after_the_alarm_with_the_lease_released():
    stall("build 2")
    room("lease", "release", check=True)  # a handover whose successor never came
    nf = len(fires())
    r = watchdog()
    assert "alarm: no progress for 5h" in r.stdout and "started: " in r.stdout, out(r)
    assert text_of(comments()[-1]).endswith("(plain join line, started by watchdog)")
    assert [body_of(x) for x in fires()[nf:]] == [JOIN.format(n=1)]


def park(n, step):
    """The lead escalates and parks: ESCALATION-N 5 hours ago, the waiting step, the lease released."""
    age_room()
    room("lease", "take", "--takeover", check=True)
    esc = say(f"ESCALATION-{n}: which one?")
    backdate(lambda c: c["id"] == esc, 300)
    set_state("waiting_for_owner=yes", f"step=waiting for owner: {step}", hours=5)
    room("lease", "release", check=True)
    return esc


def t_a_plain_start_after_a_decision_nobody_started_a_lead_for():
    park(1, "spec 3")
    decision = say("DECISION-1: the first", role="architect", ROOM_SESSION="arch")
    backdate(lambda c: c["id"] == decision, 200)
    nf, n = len(fires()), len(comments())
    r = watchdog()
    assert "alarm: no lead joined after DECISION-1" in r.stdout and "started: " in r.stdout, out(r)
    assert new_kinds(n) == ["LEAD-SILENT", "LEAD-STARTED"], new_kinds(n)
    assert text_of(comments()[-1]).endswith("(plain join line, started by watchdog)") and len(fires()) == nf + 1


def t_no_second_start_after_the_architects_start():
    park(2, "spec 4")
    decision = say("DECISION-2: the second", role="architect", ROOM_SESSION="arch")
    say("LEAD-STARTED: https://claude.ai/code/a1 (plain join line, started by architect)", role="architect",
        ROOM_SESSION="arch")  # its lead never joined
    backdate(lambda c: c["id"] == decision, 260)
    backdate(lambda c: c["id"] > decision, 200)
    nf, n = len(fires()), len(comments())
    r = watchdog()
    assert "alarm: no lead joined after DECISION-2" in r.stdout and "is this stall's start" in r.stdout, out(r)
    assert new_kinds(n) == ["LEAD-SILENT"] and len(fires()) == nf


def t_no_second_start_after_an_unconfirmed_start():
    stall("build 5")
    r = room("start-lead", "1", "architect", "--takeover", ROOM_SESSION="arch", FAKE_FIRE_STATUS="502",
             FAKE_FIRE_BODY="Bad Gateway")
    assert r.returncode == 0 and "LEAD-STARTED: unconfirmed (HTTP 502)" in text_of(comments()[-1]), out(r)
    backdate(lambda c: c["id"] == comments()[-1]["id"], 200)
    nf = len(fires())
    r = watchdog()
    assert "alarm: no progress for 5h" in r.stdout and "is this stall's start" in r.stdout and len(fires()) == nf, out(r)


def t_a_plain_start_before_any_lead_joined():
    assert "room 2 in SigorMatt/pet" in room("new", "Phase 2", check=True).stdout
    original = edit_state("PLAYBOOK.md", lambda t: re.sub(r"^room: .*$", "room: 2", t, count=1, flags=re.M))
    room("lease", "take", "--takeover", check=True)
    set_state("status=done")  # phase 1 is over
    room("lease", "release", check=True)
    try:
        opened("2", 13)
        nf = len(fires())
        r = watchdog(n="2")
        assert "alarm: no lead has joined room 2 in 12h" in r.stdout and "started: " in r.stdout, out(r)
        assert new_kinds(0, "2") == ["LEAD-SILENT", "LEAD-STARTED"], new_kinds(0, "2")
        assert [body_of(x) for x in fires()[nf:]] == [JOIN.format(n=2)]
        r = watchdog(n="2")
        assert "is this stall's start" in r.stdout and len(fires()) == nf + 1, out(r)
    finally:
        edit_state("PLAYBOOK.md", lambda t: original)
        room("lease", "take", "--takeover", check=True)
        set_state("status=running")


def t_a_takeover_after_a_lead_joined_at_waiting_and_died():
    park(3, "spec 5")
    decision = say("DECISION-3: the third", role="architect", ROOM_SESSION="arch")
    started = say("LEAD-STARTED: https://claude.ai/code/a2 (plain join line, started by architect)", role="architect",
                  ROOM_SESSION="arch")
    room("lease", "take", check=True, ROOM_SESSION="L2")
    joined = say("LEAD ONLINE", ROOM_SESSION="L2")  # then it dies before moving the step on
    backdate(lambda c: c["id"] in (decision, started), 260)
    backdate(lambda c: c["id"] == joined, 200)  # a new stall, from its LEAD ONLINE (cold M6b R1-1)
    nf, n = len(fires()), len(comments())
    r = watchdog()
    assert f"alarm: no progress for 3h20m (LEAD ONLINE #{joined} at " in r.stdout and "started: " in r.stdout, out(r)
    assert new_kinds(n) == ["LEAD-SILENT", "LEAD-STARTED"]
    assert text_of(comments()[-1]).endswith("(takeover join line, started by watchdog)") and len(fires()) == nf + 1


def t_no_start_while_a_lead_talks():
    stall("build 6")
    talk = say("STATUS: builders still running")
    nf, n = len(fires()), len(comments())
    r = watchdog()
    assert "alarm: no progress for 5h" in r.stdout and f"note: no start: the lead posted #{talk} at " in r.stdout, out(r)
    assert new_kinds(n) == ["LEAD-SILENT"] and len(fires()) == nf
    backdate(lambda c: c["id"] == talk, 200)  # silent for silent-after now
    r = watchdog()
    assert "started: " in r.stdout and len(fires()) == nf + 1, out(r)


def t_a_definite_failure_is_retried_at_the_next_run():
    stall("build 7")
    nf, n = len(fires()), len(comments())
    r = watchdog(FAKE_FIRE_STATUS="503", FAKE_FIRE_BODY="overloaded")
    assert "start failed: lead task not started: HTTP 503: overloaded; the next run tries again" in r.stdout, out(r)
    assert new_kinds(n) == ["LEAD-SILENT"] and len(fires()) == nf + 1
    r = watchdog()
    assert "already reports this stall" in r.stdout and "started: " in r.stdout and len(fires()) == nf + 2, out(r)
    assert new_kinds(n) == ["LEAD-SILENT", "LEAD-STARTED"]


def t_not_configured_or_refused_prints_a_note():
    stall("build 8")
    nf, n = len(fires()), len(comments())
    r = watchdog(ROOM_FIRE_TOKEN_PET=None)
    assert "note: no start: the lead task isn't configured" in r.stdout and len(fires()) == nf, out(r)
    r = watchdog(FAKE_FIRE_STATUS="401", FAKE_FIRE_BODY='{"error": {"message": "bad token"}}')
    assert "note: no lead started: token rejected (HTTP 401)" in r.stdout and len(fires()) == nf + 1, out(r)
    set_issue_state("1", "closed")
    try:
        r = watchdog()
        assert "note: no lead started: refused: room 1 is closed" in r.stdout and len(fires()) == nf + 1, out(r)
    finally:
        set_issue_state("1", "open")
    assert new_kinds(n) == ["LEAD-SILENT"], "the alarm alone"


def t_a_failed_alarm_post_means_no_fire():
    stall("build 9")
    nf, n = len(fires()), len(comments())
    r = watchdog(FAKE_GH_FAIL_POSTS="1", FAKE_GH_FAIL_COUNTER=os.path.join(tmp, "alarm-post-fails"))
    assert r.returncode == 1 and "Bad Gateway" in r.stderr, out(r)
    assert len(fires()) == nf and len(comments()) == n, "no alarm, so no start"
    r = watchdog()
    assert "alarm: no progress for 5h" in r.stdout and "started: " in r.stdout, out(r)
    assert new_kinds(n) == ["LEAD-SILENT", "LEAD-STARTED"]


# --- B-6: reminders while a room waits on Matthew

def t_a_reminder_while_a_request_waits_on_matthew():
    esc = park(4, "gate 10")
    quiet = "quiet: step is waiting for owner: gate 10"
    nf = len(fires())
    assert watchdog().stdout.strip() == quiet, "under 12 hours"
    backdate(lambda c: c["id"] == esc, 730)
    asked = next(c for c in comments() if c["id"] == esc)["created_at"]
    text = f"LEAD-SILENT: still waiting for Matthew: ESCALATION-4 since {asked} (step waiting for owner: gate 10)"
    n = len(comments())
    r = watchdog()
    assert "alarm: still waiting for Matthew: ESCALATION-4" in r.stdout, out(r)
    assert [text_of(c) for c in comments()[n:]] == [f"{text} (buzz sent)"], out(r)
    assert "already reports this stall" in watchdog().stdout and len(comments()) == n + 1
    backdate(lambda c: c["id"] > esc, 730)  # 12 hours on: again, and a failed buzz is retried at the next run
    r = watchdog(ROOM_NTFY_TOPIC=None)
    assert text_of(comments()[-1]) == f"{text} (buzz failed: ROOM_NTFY_TOPIC is not set)", out(r)
    r = watchdog()
    assert "(again: the last buzz failed)" in r.stdout and text_of(comments()[-1]) == f"{text} (buzz sent)", out(r)
    assert len(comments()) == n + 3 and len(fires()) == nf, "no start on this path"
    # a merge hold waits the same way
    age_room()  # all of the above came before it
    hold = say("MERGE-HOLD-5: sensitive path")
    backdate(lambda c: c["id"] == hold, 730)
    r = watchdog()
    assert "alarm: still waiting for Matthew: MERGE-HOLD-5" in r.stdout and len(fires()) == nf, out(r)


def t_no_waiting_reminder_after_a_decision_or_with_the_lease_held():
    esc = park(6, "gate 11")
    backdate(lambda c: c["id"] == esc, 730)
    say("DECISION-6: go ahead", role="architect", ROOM_SESSION="arch")  # under silent-after: no lead due yet
    n = len(comments())
    assert watchdog().stdout.strip() == "quiet: step is waiting for owner: gate 11"
    assert len(comments()) == n
    esc = park(7, "gate 12")
    backdate(lambda c: c["id"] == esc, 730)
    room("lease", "take", check=True)  # a lead holds the lease: it's running, a stall like any other
    r = watchdog()
    assert "still waiting for Matthew" not in r.stdout and \
        not any("still waiting for Matthew" in text_of(c) for c in comments()[n:]), out(r)


def t_the_state_unreadable_reminder_is_retried():
    age_room()
    tip = g("--git-dir", PET, "rev-parse", "agent-room/state").stdout.strip()
    g("--git-dir", PET, "update-ref", "-d", "refs/heads/agent-room/state")
    try:
        nf, n = len(fires()), len(comments())
        assert "alarm: state unreadable (" in watchdog().stdout
        backdate(lambda c: c["id"] > comments()[n - 1]["id"], 730)
        r = watchdog(ROOM_NTFY_TOPIC=None)
        assert "alarm: still state unreadable" in r.stdout, out(r)
        r = watchdog()
        assert "alarm: still state unreadable (agent-room/state doesn't exist in SigorMatt/pet) (again: the last " \
            "buzz failed)" in r.stdout, out(r)
        assert text_of(comments()[-1]).endswith("(buzz sent)") and len(comments()) == n + 3
        assert len(fires()) == nf, "no start after a state unreadable alarm"
    finally:
        g("--git-dir", PET, "update-ref", "refs/heads/agent-room/state", tip)


setup()
for name, fn in list(globals().items()):
    if name.startswith("t_"):
        test(name[2:], fn)
shutil.rmtree(tmp, ignore_errors=True)
print("all passed")
