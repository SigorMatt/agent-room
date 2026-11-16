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


def t_pre_start_alarms_and_reminds_without_a_start():
    # cold M6d R1-6: before any lead joined, the architect decides; the watchdog alarms and reminds, as in M6b
    assert "room 2 in SigorMatt/pet" in room("new", "Phase 2", check=True).stdout
    original = edit_state("PLAYBOOK.md", lambda t: re.sub(r"^room: .*$", "room: 2", t, count=1, flags=re.M))
    room("lease", "take", "--takeover", check=True)
    set_state("status=done")  # phase 1 is over
    room("lease", "release", check=True)
    try:
        opened("2", 13)
        nf = len(fires())
        r = watchdog(n="2")
        assert "alarm: no lead has joined room 2 in 12h" in r.stdout and "started:" not in r.stdout, out(r)
        assert new_kinds(0, "2") == ["LEAD-SILENT"], new_kinds(0, "2")
        assert "already reports this stall" in watchdog(n="2").stdout
        backdate(lambda c: True, 730, "2")
        r = watchdog(n="2")
        assert "alarm: still no lead has joined room 2" in r.stdout and "started:" not in r.stdout, out(r)
        assert new_kinds(0, "2") == ["LEAD-SILENT", "LEAD-SILENT"] and len(fires()) == nf
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


def t_no_start_when_a_lead_posted_before_the_first_alarm():
    # cold M6d R1-4, R1-1: a lead that posted within silent-after before the alarm may be working quietly (a long
    # builder run after its STATUS): no start at that run, nor at any later one; the architect decides
    stall("build 6")
    talk = say("STATUS: three builders running in the background")
    nf, n = len(fires()), len(comments())
    r = watchdog()
    assert "alarm: no progress for 5h" in r.stdout and f"note: no start: the lead posted STATUS #{talk} at " in \
        r.stdout and "it may be working quietly" in r.stdout, out(r)
    assert new_kinds(n) == ["LEAD-SILENT"] and len(fires()) == nf
    first = comments()[n]["id"]
    backdate(lambda c: c["id"] == talk, 250)  # hours later, nothing new: the same stall, the same first alarm
    backdate(lambda c: c["id"] == first, 249)
    r = watchdog()
    assert "already reports this stall" in r.stdout and f"the lead posted STATUS #{talk}" in r.stdout, out(r)
    assert len(fires()) == nf and len(comments()) == n + 1


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


# --- after cold review round 1 of M6d

def t_no_start_while_paused_or_stopped_with_the_lease_held():
    # cold M6d R1-2: a lead that wrote paused or stopped and died before its post and release isn't taken over: a
    # takeover would set the status back to running
    for status in ("paused", "stopped"):
        stall(f"build 50 {status}")
        set_state(f"status={status}")
        nf, n = len(fires()), len(comments())
        r = watchdog()
        assert f"note: status is {status}, but L1 still holds the lease, so it counts as running" in r.stdout, out(r)
        assert "alarm: no progress for 5h" in r.stdout and f"note: no start: status is {status} (the lease is still " \
            "held): the architect decides" in r.stdout, out(r)
        assert new_kinds(n) == ["LEAD-SILENT"] and len(fires()) == nf
        set_state("status=running")


def t_a_waiting_reminder_doesnt_stand_in_for_a_decisions_alarm():
    # cold M6d R1-3: a reminder for ESCALATION-3 posted after DECISION-2 is not DECISION-2's alarm
    age_room()
    room("lease", "take", "--takeover", check=True)
    e2 = say("ESCALATION-2: which font?")
    e3 = say("ESCALATION-3: which colour?")
    set_state("waiting_for_owner=yes", "step=waiting for owner: gate 40", hours=15)
    room("lease", "release", check=True)
    backdate(lambda c: c["id"] == e2, 900)
    backdate(lambda c: c["id"] == e3, 840)
    decision = say("DECISION-2: serif", role="architect", ROOM_SESSION="arch")  # under silent-after: no lead due yet
    backdate(lambda c: c["id"] == decision, 60)
    n = len(comments())
    r = watchdog()
    assert "alarm: still waiting for Matthew: ESCALATION-3" in r.stdout, out(r)
    reminder = comments()[n]["id"]
    backdate(lambda c: c["id"] == decision, 200)  # now the decision is silent-after old, and no lead joined
    backdate(lambda c: c["id"] == reminder, 190)
    nf, n = len(fires()), len(comments())
    r = watchdog()
    assert "alarm: no lead joined after DECISION-2" in r.stdout and "started: " in r.stdout, out(r)
    assert new_kinds(n) == ["LEAD-SILENT", "LEAD-STARTED"], new_kinds(n)
    assert text_of(comments()[n]).startswith("LEAD-SILENT: no lead joined after DECISION-2 (step waiting for owner: "
                                             "gate 40)") and len(fires()) == nf + 1


def t_start_lead_seen_refuses_once_the_room_moved_on():
    # cold M6d R1-1: an architect's starter task passes the room's newest comment ID when it decided; it starts
    # nothing if a lead message, or a LEAD-STARTED from anyone, came after it
    stall("build 60")
    seen = comments()[-1]["id"]
    say("DECISION-9: unrelated", role="architect", ROOM_SESSION="arch")  # not a lead message, not a start
    nf = len(fires())
    r = room("start-lead", "1", "architect", "--takeover", "--seen", str(seen), ROOM_SESSION="arch")
    assert r.returncode == 0 and "started: " in r.stdout and len(fires()) == nf + 1, out(r)
    stall("build 61")
    seen = comments()[-1]["id"]
    r = watchdog()  # the watchdog's start comes first
    assert "started: " in r.stdout, out(r)
    started = comments()[-1]["id"]
    backdate(lambda c: c["id"] > seen, 40)  # the starter task runs 40 minutes later
    nf, n = len(fires()), len(comments())
    r = room("start-lead", "1", "architect", "--takeover", "--seen", str(seen), ROOM_SESSION="arch")
    assert r.returncode == 3 and r.stderr.strip().startswith(f"refused: the room moved on after #{seen}: "
                                                             f"LEAD-STARTED #{started} at ") and \
        r.stderr.strip().endswith("; read the room again"), out(r)
    assert len(fires()) == nf and len(comments()) == n
    stall("build 62")
    seen = comments()[-1]["id"]
    talk = say("STATUS: still here")
    r = room("start-lead", "1", "architect", "--takeover", "--seen", str(seen), ROOM_SESSION="arch")
    assert r.returncode == 3 and f"refused: the room moved on after #{seen}: STATUS #{talk} at " in r.stderr, out(r)
    assert len(fires()) == nf


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


# --- after Qodo's review of PR #14

def handover(step, minutes=280):
    """L1 holds the lease and hands over at STEP, recorded five hours ago, then starts its successor with start-lead
    (LEAD.md section 6), which posts LEAD-STARTED as the lead. Returns the last comment ID before the HANDOFF; the
    caller backdates what follows."""
    age_room()
    room("lease", "take", "--takeover", check=True)
    before = comments()[-1]["id"]
    room("handoff", "1", "--step", step, "--cursor", "none", check=True, **ago(5)[1])
    room("start-lead", "1", "lead", check=True)
    assert text_of(comments()[-1]).endswith("(plain join line, started by lead)"), text_of(comments()[-1])
    return before


def t_a_start_after_a_handover_whose_successor_never_joined():
    # qodo PR #14 finding 2: a lead's own handover LEAD-STARTED isn't this stall's start; its successor is what stalled
    before = handover("build 30")
    backdate(lambda c: c["id"] > before, 280)
    nf, n = len(fires()), len(comments())
    r = watchdog()
    assert "alarm: no progress for 5h" in r.stdout and "started: https://claude.ai/code/" in r.stdout, out(r)
    assert new_kinds(n) == ["LEAD-SILENT", "LEAD-STARTED"], new_kinds(n)
    assert text_of(comments()[-1]).endswith("(plain join line, started by watchdog)") and len(fires()) == nf + 1


def t_a_start_after_a_handover_whose_successor_joined_and_died():
    # qodo PR #14 finding 2: the successor joined, then died before any progress: a takeover; when that lead dies too,
    # it's the same stall, and the watchdog starts no other
    before = handover("build 31")
    room("lease", "take", check=True, ROOM_SESSION="L2")
    say("LEAD ONLINE", ROOM_SESSION="L2")
    backdate(lambda c: c["id"] > before, 280)
    nf, n = len(fires()), len(comments())
    r = watchdog()
    assert "alarm: no progress for 5h" in r.stdout and "started: https://claude.ai/code/" in r.stdout, out(r)
    assert new_kinds(n) == ["LEAD-SILENT", "LEAD-STARTED"], new_kinds(n)
    assert text_of(comments()[-1]).endswith("(takeover join line, started by watchdog)") and len(fires()) == nf + 1
    first = comments()[n]["id"]
    room("lease", "take", "--takeover", check=True, ROOM_SESSION="T3")
    t3 = say("LEAD ONLINE", ROOM_SESSION="T3")  # the takeover lead joins, then dies too
    backdate(lambda c: first <= c["id"] < t3, 210)
    backdate(lambda c: c["id"] == t3, 200)
    r = watchdog()
    assert "already reports this stall" in r.stdout and "is this stall's start" in r.stdout, out(r)
    assert len(fires()) == nf + 1 and len(comments()) == n + 3


def t_no_start_after_a_lead_joined_after_the_alarm_with_no_lead_started():
    # qodo PR #14 finding 1: Matthew started a lead in the Code tab, so no LEAD-STARTED was posted; its LEAD ONLINE
    # after the stall's first alarm makes it this stall's start
    stall("build 32")
    nf, n = len(fires()), len(comments())
    r = watchdog(ROOM_FIRE_TOKEN_PET=None)
    assert "alarm: no progress for 5h" in r.stdout and "the lead task isn't configured" in r.stdout, out(r)
    first = comments()[n]["id"]
    room("lease", "take", "--takeover", check=True, ROOM_SESSION="T4")
    joined = say("LEAD ONLINE", ROOM_SESSION="T4")  # then it dies, and is silent for silent-after
    backdate(lambda c: c["id"] == first, 260)
    backdate(lambda c: c["id"] == joined, 200)
    r = watchdog()
    assert "already reports this stall" in r.stdout and f"note: no start: the lead posted LEAD ONLINE #{joined} at " \
        in r.stdout and f"after this stall's first alarm #{first}: a lead joined or spoke" in r.stdout, out(r)
    assert len(fires()) == nf and len(comments()) == n + 2


def t_the_architects_start_still_blocks_a_stalls_start():
    # qodo PR #14: only a lead's own LEAD-STARTED stopped counting; the architect's still is this stall's start
    stall("build 33")
    started = say("LEAD-STARTED: https://claude.ai/code/a9 (takeover join line, started by architect)",
                  role="architect", ROOM_SESSION="arch")
    backdate(lambda c: c["id"] == started, 200)  # its lead never joined
    nf = len(fires())
    r = watchdog()
    assert "alarm: no progress for 5h" in r.stdout and f"note: LEAD-STARTED #{started} at " in r.stdout, out(r)
    assert len(fires()) == nf


def push_mission(hours, branch="mission/M1-greet"):
    """Push BRANCH to a new commit on main, committed HOURS ago: progress outside the state branch."""
    t, dated = ago(hours)
    g("checkout", "-q", "-B", branch, "origin/main")
    with open(os.path.join(CHECKOUT, "work.txt"), "w") as f:
        f.write(f"{branch} {t} {time.time()}\n")
    g("add", "-A")
    g("commit", "-q", "-m", f"work on {branch}", **dated)
    g("push", "-q", "-f", "origin", f"HEAD:refs/heads/{branch}")


def drop_mission(branch="mission/M1-greet"):
    g("push", "-q", "origin", "--delete", branch)
    g("checkout", "-q", "-B", "main", "origin/main")


def t_an_outage_after_an_ordinary_alarm_gets_a_new_first_alarm():
    # qodo PR #14 finding 4: only the newest run of state unreadable alarms counts, the ones after the last other alarm
    age_room()
    push_mission(14)  # progress outside the state branch, 14 hours ago
    tip = g("--git-dir", PET, "rev-parse", "agent-room/state").stdout.strip()
    unreadable = "LEAD-SILENT: state unreadable (agent-room/state doesn't exist in SigorMatt/pet)"
    try:
        g("--git-dir", PET, "update-ref", "-d", "refs/heads/agent-room/state")
        n = len(comments())
        assert "alarm: state unreadable (" in watchdog().stdout
        outage = comments()[n]["id"]
        backdate(lambda c: c["id"] == outage, 600)
        g("--git-dir", PET, "update-ref", "refs/heads/agent-room/state", tip)  # the state comes back
        room("lease", "take", "--takeover", check=True)
        set_state("step=build 34", hours=6)  # a lead moved on, then stalled
        r = watchdog(ROOM_FIRE_TOKEN_PET=None)
        assert "alarm: no progress for 6h" in r.stdout, out(r)
        tip = g("--git-dir", PET, "rev-parse", "agent-room/state").stdout.strip()
        g("--git-dir", PET, "update-ref", "-d", "refs/heads/agent-room/state")  # a new outage, no progress since
        m = len(comments())
        r = watchdog()
        assert "alarm: state unreadable (" in r.stdout, out(r)
        assert [text_of(c) for c in comments()[m:]] == [f"{unreadable} (buzz sent)"], out(r)
    finally:
        g("--git-dir", PET, "update-ref", "refs/heads/agent-room/state", tip)
        drop_mission()


def t_a_state_unreadable_alarm_during_the_wait_doesnt_delay_the_reminder():
    # qodo PR #14 finding 5: only this request's own reminders count as its alarms
    esc = park(8, "gate 20")
    backdate(lambda c: c["id"] == esc, 730)
    outage = say("LEAD-SILENT: state unreadable (agent-room/state doesn't exist in SigorMatt/pet) (buzz sent)",
                 role="watchdog", ROOM_SESSION="wd")
    backdate(lambda c: c["id"] == outage, 400)  # posted while it waited; the state came back since
    n = len(comments())
    r = watchdog()
    assert "alarm: still waiting for Matthew: ESCALATION-8" in r.stdout and len(comments()) == n + 1, out(r)


def t_no_waiting_reminder_when_no_room_is_recorded():
    # qodo PR #14 finding 6: a room neither PLAYBOOK.md (room: 0) nor the machine block records gets no reminder
    esc = park(9, "gate 21")
    room("lease", "take", check=True)
    set_state("room=none")
    room("lease", "release", check=True)
    backdate(lambda c: c["id"] == esc, 730)
    n = len(comments())
    try:
        r = watchdog()
        assert r.stdout.strip() == "quiet: step is waiting for owner: gate 21" and len(comments()) == n, out(r)
    finally:
        room("lease", "take", check=True)
        set_state("room=1")


setup()
for name, fn in list(globals().items()):
    if name.startswith("t_"):
        test(name[2:], fn)
shutil.rmtree(tmp, ignore_errors=True)
print("all passed")
