#!/usr/bin/env python3
"""agent-room: a chat room for agents, backed by one GitHub issue.

A room is an issue (labelled agent-room) in the repo the agents are working on;
each message is a comment tagged with its sender's role and session. Everything
goes through the `gh` CLI, so auth is whatever `gh` already has: the GitHub proxy
in Claude chat and cloud sessions, or `gh auth login` on your own machine.

  room.py new "title"             create a room, print its number
  room.py rooms                   list open rooms
  room.py say   N ROLE [TEXT|-]   post a message (TEXT, or stdin if omitted or -)
  room.py read  N ROLE            print unseen messages once, without blocking
  room.py read  N ROLE --from ID  move the cursor to comment ID first, then read what follows
  room.py read  N --all           print the whole transcript
  room.py wait  N ROLE            block until someone else speaks, print, exit
  room.py cursor N ROLE           print the last comment ID this role has read, or none
  room.py close N ROLE [TEXT]     close the room and post a closing note (buzzes like say)
  room.py ping                    send a test phone notification
  room.py state init|init-lead|path|sync|commit|get|set|next   the playbook on agent-room/state
  room.py lease take|release|check   the lead lease (exit 3: stand down; 5: not the holder)
  room.py preflight --role architect|lead [--fix]              check repo, state branch, environment
  room.py gate  PR [--mission M<k>] [--allow-hold 5 --decision DECISION-<n>]   the merge gate
  room.py merge PR --sha SHA [--allow-hold 5 --decision DECISION-<n>]        gate, then merge naming SHA
  room.py watchdog N [--silent-after 3h]   the watchdog task: LEAD-SILENT (buzzes) when no progress, or no lead
                                           joined after a DECISION; reminders, also while a request waits on
                                           Matthew; one lead start per stall; never writes state
  room.py join-line N [--takeover]         print the line that starts a lead
  room.py start-lead N ROLE [--takeover] [--force] [--seen ID] [--replacing SESSION]   start a lead through the lead
                                           task and post LEAD-STARTED (exit 1 try once more, 3 refused, 6 not
                                           configured or rejected)
  room.py lead-task-prompt                 print the prompt of this repo's lead task
  room.py handoff N --step STEP --cursor ID   post HANDOFF, record step and cursor, release the lease, print the join line
  room.py intent N "INTENT"                record before acting (post KIND intents note the room's last comment)
  room.py reconcile N                      for a joining lead: the recorded state next to GitHub's facts
  room.py budget                           the mission's elapsed time against its budget (exit 6 over)

Every room command takes --repo OWNER/NAME. Without it: $ROOM_REPO, else the
GitHub remote of the current checkout. --session SID names this participant;
without it: $ROOM_SESSION, else the first 8 characters of $CLAUDE_CODE_SESSION_ID,
else the hostname. read and wait hide only this role's messages from this session,
so a lead sees other leads' messages.

Only the roles lead, architect and watchdog post; any role may read. A message's
kind is its leading token, even inside markdown (**ESCALATION-3**): STATUS,
ESCALATION-3, MERGE-HOLD-4, LEAD ONLINE, ACK DECISION-2. The role guard refuses
other roles, and kinds that belong to another role (exit 2, nothing posted).
`say` and `close` push a phone notification through ntfy for ESCALATION,
MERGE-HOLD, NEXT-LEAD-NEEDED, PAUSED, STOPPED, DONE and LEAD-SILENT; --buzz
forces one, --no-buzz suppresses it. A push carries only the kind and the room,
never the content.

wait exits 0 with new messages (its last line is [cursor: ID]), 3 on timeout
(re-arm it), 4 if the room is closed.

gate prints one line per check and a verdict: exit 0 PASS, 3 WAIT (checks pending),
5 lease lost, 6 FAIL with the hold reasons. merge exits 3 if the head moved (re-run
the gate) and 6 if GitHub finds the PR not mergeable.

Environment:
  ROOM_REPO         default repo for rooms
  ROOM_SESSION      this participant's session ID (see --session)
  ROOM_TRUST        comma-separated GitHub logins whose comments count besides your gh login's
  ROOM_STATE        where read cursors live (default ~/.agent-room)
  ROOM_STATE_DIR    the state branch's worktree (default ~/agent-room-state/OWNER__NAME)
  ROOM_STATE_REMOTE git URL to clone the state branch from when not run inside the project's checkout
  ROOM_NTFY_TOPIC   ntfy topic your phone subscribes to (needed for buzzes and ping)
  ROOM_NTFY_SERVER  ntfy server (default https://ntfy.sh)
  ROOM_NTFY_TOKEN   optional ntfy access token (only raises limits on a paid ntfy.sh tier)
  ROOM_FIRE_TOKEN_<NAME>  the lead task's API trigger token for repo NAME (in upper case, every character
                    other than A-Z and 0-9 as _: pet-todo is ROOM_FIRE_TOKEN_PET_TODO); never printed
  ROOM_FIRE_TOKEN   the token when ROOM_FIRE_TOKEN_<NAME> is unset
  ROOM_FIRE_URL     the API that start-lead calls (default https://api.anthropic.com)
  ROOM_FIRE_BETA    start-lead's anthropic-beta header (default experimental-cc-routine-2026-04-01)
"""
import argparse
import datetime
import calendar
import html
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time

VERSION = "main"  # a release sets this to its tag (v1.0.0); every link room.py writes points at it

HOME_REPO = "SigorMatt/agent-room"  # where this client and its protocol live
LABEL = "agent-room"
STATE = os.path.expanduser(os.environ.get("ROOM_STATE", "~/.agent-room"))
SESSION_RE = r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}"
MARK = re.compile(r"<!-- agent-room role=([a-z][a-z0-9-]*)(?: session=(" + SESSION_RE + r"))? -->\n"
                  r"(?:\*\*\[[a-z0-9-]+(?: · [^\]\n]+)?\]\*\*\n\n?)?")
FOOTER = re.compile(r"\s*\n---\n_Generated by \[Claude Code\]\([^)]*\)_\s*$")  # added by Claude's GitHub proxy
MAX_CHARS = 60000  # GitHub caps a comment at 65536
ME = f"python3 {sys.argv[0]}"

# message kinds, after leading whitespace and markdown decoration: the multi-word ones first, else the
# leading run of capitalised words joined by '-'. A kind ends where no letter or digit follows, so
# "**ESCALATION-3**:" and "_DONE_" parse too.
DECORATION = re.compile(r"^[\s*_`>#]+")
MULTIWORD_KIND = re.compile(r"(LEAD ONLINE|ACK DECISION-\d+|ACK CHANGE-\d+)(?![A-Za-z0-9])")
KIND = re.compile(r"([A-Z]{2,}(?:-[A-Z]+)*(?:-\d+)?)(?![A-Za-z0-9])")
BUZZ_KINDS = {"ESCALATION", "MERGE-HOLD", "NEXT-LEAD-NEEDED", "PAUSED", "STOPPED", "DONE", "LEAD-SILENT"}
LEAD_CANNOT = {"DECISION", "CHANGE", "PAUSE", "STOP"}
ARCHITECT_CANNOT = {"PLAN", "LEAD ONLINE", "STATUS", "ESCALATION", "MERGE-HOLD", "HANDOFF",
                    "NEXT-LEAD-NEEDED", "PAUSED", "STOPPED", "DONE"}  # and every ACK
WATCHDOG_CAN = {"LEAD-SILENT", "LEAD-STARTED"}  # it alarms, and starts one lead per stall (M6d, B-5)
POSTING_ROLES = ("lead", "architect", "watchdog")  # anyone else may read, never post

REPO = None         # set in main()
TRUST = set()       # set in main()
SESSION_OPT = None  # --session, set in main()


class GhError(RuntimeError):
    pass


def gh(path, method="GET", body=None):
    cmd = ["gh", "api", "-X", method, path]
    if body is not None:
        cmd += ["--input", "-"]
    try:
        r = subprocess.run(cmd, input=json.dumps(body) if body is not None else None,
                           capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise GhError(f"gh api {path} timed out")
    if r.returncode != 0:
        raise GhError((r.stderr or r.stdout).strip() or f"gh exited {r.returncode}")
    return json.loads(r.stdout) if r.stdout.strip() else None


class StateError(RuntimeError):
    """A git command or the state branch failed."""


def git(*args, cwd=None, check=True, timeout=180):
    # a hook or another git command may have set these; they would override -C / cwd
    env = {k: v for k, v in os.environ.items()
           if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR")}
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        r = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise StateError(f"git {args[0]}: {e}")
    if check and r.returncode != 0:
        raise StateError(f"git {args[0]}: {(r.stderr or r.stdout).strip() or f'exited {r.returncode}'}")
    return r


def git_out(*args, cwd=None):
    return git(*args, cwd=cwd).stdout.strip()


def repo_of_url(url):
    """OWNER/NAME from a GitHub (or Claude proxy) git URL, or None."""
    m = re.search(r"(?:github\.com[:/]+|/git/)([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def repo_from_checkout():
    try:
        url = git("remote", "get-url", "origin", check=False, timeout=10).stdout.strip()
    except StateError:
        return None
    return repo_of_url(url)


def default_trust():
    try:
        return {gh("user")["login"].lower()}
    except (GhError, KeyError, TypeError):
        return {REPO.split("/")[0].lower()}


def doc_url(path, version=None):
    """A link to a file of agent-room itself, at the version this client belongs to (or VERSION given)."""
    return f"https://github.com/{HOME_REPO}/blob/{version or VERSION}/{path}"


# --- identity

def session_id(a=None):
    """This participant's session: --session (from the parsed arguments a, else as main stored it),
    else $ROOM_SESSION, else the first 8 characters of $CLAUDE_CODE_SESSION_ID, else the hostname."""
    given = getattr(a, "session", None) or SESSION_OPT or os.environ.get("ROOM_SESSION", "").strip()
    if given:
        if not re.fullmatch(SESSION_RE, given):
            sys.exit(f"bad session {given!r}: use up to 64 letters, digits, '.', '_' or '-'")
        return given
    for candidate in (os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()[:8], socket.gethostname()):
        sid = re.sub(r"[^A-Za-z0-9._-]", "-", candidate).strip("._-")[:64]
        if sid:
            return sid
    return "unknown"


def is_own(m, role, session):
    """Sent by this participant: a trusted author, same role and session. A message from before
    sessions has none, so its role alone decides, as it used to. Anyone can copy a role and
    session tag, so an untrusted comment is never one's own."""
    return m["role"] == role and m["session"] in (None, session) and trusted(m)


# --- messages

def comments(room, since=None):
    out, page = [], 1
    while True:
        q = f"per_page=100&page={page}" + (f"&since={since}" if since else "")
        batch = gh(f"repos/{REPO}/issues/{room}/comments?{q}")
        out += batch
        if len(batch) < 100:
            return out
        page += 1


def parse(c):
    body = FOOTER.sub("", (c.get("body") or "").replace("\r\n", "\n"))
    m = MARK.match(body)
    return {
        "id": c["id"],
        "role": m.group(1) if m else "human",
        "session": m.group(2) if m else None,
        "author": (c.get("user") or {}).get("login", "?"),
        "at": c["created_at"],
        "text": (body[m.end():] if m else body).strip(),
    }


def trusted(m):
    return m["author"].lower() in TRUST


def message_kind(text):
    """The message's leading token (ESCALATION-3, MERGE-HOLD-4, LEAD ONLINE...), or None.
    Leading whitespace and markdown decoration (* _ ` > #) don't hide it."""
    text = DECORATION.sub("", text or "")
    m = MULTIWORD_KIND.match(text) or KIND.match(text)
    return m.group(1) if m else None


def base_kind(kind):
    """The kind without its number: ESCALATION-3 -> ESCALATION, ACK DECISION-2 -> ACK DECISION."""
    return re.sub(r"-\d+$", "", kind) if kind else None


def guard_error(role, kind):
    """Why ROLE may not send a message of KIND, or None if it may."""
    base = base_kind(kind)
    if role not in POSTING_ROLES:
        return f"role {role} cannot post; only {', '.join(POSTING_ROLES)} do"
    if role == "lead" and base in LEAD_CANNOT:
        return f"a lead cannot send {kind}; that is for the architect or Matthew"
    if role == "architect" and (base in ARCHITECT_CANNOT or re.match(r"ACK\b", base or "")):
        return f"the architect cannot send {kind}; that is for the lead"
    if role == "watchdog" and base not in WATCHDOG_CAN:
        return f"the watchdog can send only LEAD-SILENT and LEAD-STARTED, not {kind or 'a message without a kind'}"
    return None


def check_role(role, kind):
    err = guard_error(role, kind)
    if err:
        print(f"refused: {err}. Nothing was posted.", file=sys.stderr)
        sys.exit(2)


def message_text(text):
    """The text to post: TEXT, or stdin when it is omitted or '-'. Exits if empty or too long."""
    if text is None or text == "-":
        text = sys.stdin.read()
    text = text.strip()
    if not text:
        sys.exit("empty message")
    if len(text) > MAX_CHARS:
        sys.exit(f"message is {len(text)} chars; keep it under {MAX_CHARS} and link to files or commits instead")
    return text


def post(room, role, text):
    sid = session_id()
    body = f"<!-- agent-room role={role} session={sid} -->\n**[{role} · {sid}]**\n\n{text}\n"
    return gh(f"repos/{REPO}/issues/{room}/comments", "POST", {"body": body})


# --- read cursors: the last comment each participant has seen, one small file per repo+room+role+session, so
# two sessions of one role on one machine (an old and a new lead) don't move each other's cursor

def cursor_file(room, role):
    return os.path.join(STATE, REPO.replace("/", "__"), f"{room}-{role}-{session_id()}.json")


def load_cursor(room, role):
    try:
        with open(cursor_file(room, role)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save_cursor(room, role, m):
    path = cursor_file(room, role)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"id": m["id"], "at": m["at"]}, f)


def cursor_id(room, role):
    """The ID of the last comment this role and session has read, or None."""
    cur = load_cursor(room, role)
    return (cur or {}).get("id") or None


def move_cursor(room, role, ref):
    """Point this ROLE and session's cursor at comment REF of this room, or at the room's start for 'none'."""
    if ref == "none":
        save_cursor(room, role, {"id": 0, "at": None})
        return
    c = gh(f"repos/{REPO}/issues/comments/{ref}")
    if not (c.get("issue_url") or "").endswith(f"/issues/{room}"):
        sys.exit(f"comment {ref} is not in room {room}")
    save_cursor(room, role, {"id": c["id"], "at": c["created_at"]})


def unseen(room, role):
    """Messages from others this role hasn't seen; advances the cursor past them.

    Others are everyone but this role in this session. With no cursor (new or wiped
    machine), everything after this participant's own last trusted message counts as
    unseen, so a restarted participant picks up where it left off, and a forged tag
    can't make it skip anything.
    """
    sid = session_id()
    cur = load_cursor(room, role)
    msgs = [parse(c) for c in comments(room, (cur or {}).get("at"))]
    if cur:
        after = cur["id"]
    else:
        mine = [m["id"] for m in msgs if is_own(m, role, sid)]
        after = max(mine) if mine else 0
    fresh = [m for m in msgs if m["id"] > after]
    others = [m for m in fresh if not is_own(m, role, sid)]
    ignored = [m for m in others if not trusted(m)]
    if ignored:
        names = ", ".join(sorted({m["author"] for m in ignored}))
        print(f"[ignored {len(ignored)} message(s) from untrusted authors: {names}]", file=sys.stderr)
    if fresh:
        save_cursor(room, role, max(fresh, key=lambda m: m["id"]))
    return [m for m in others if trusted(m)]


def show(msgs):
    for m in msgs:
        if m["role"] == "human":
            who = f"human ({m['author']})"
        else:
            who = m["role"] + (f" · {m['session']}" if m["session"] else "")
        flag = "" if trusted(m) else " UNTRUSTED"
        print(f"--- [{who}]{flag} #{m['id']} {m['at']}")
        print(m["text"])
        print()


def is_closed(room):
    return gh(f"repos/{REPO}/issues/{room}")["state"] == "closed"


def hint(cmd, room, role, extra=""):
    session = f" --session {SESSION_OPT}" if SESSION_OPT else ""
    return f"{ME} {cmd} {room} {role}{extra} --repo {REPO}{session}"


# --- phone notifications

CURL_TIMEOUT = 30  # seconds; curl's own -m 20 normally ends it first


def scrub(text, secrets):
    """TEXT with each secret (the ntfy topic, the token) replaced by ***. A short secret is replaced
    only where it stands alone, so it can't mangle ordinary words."""
    for secret in filter(None, secrets):
        pattern = re.escape(secret)
        if len(secret) < 6:
            pattern = rf"(?<![A-Za-z0-9_-]){pattern}(?![A-Za-z0-9_-])"
        text = re.sub(pattern, "***", text)
    return text


def buzz(title, message, click=None):
    """Push a phone notification through ntfy. Never raises; returns an error string, or None if sent.
    The error never echoes curl's argv, and never holds the topic or the token."""
    topic = os.environ.get("ROOM_NTFY_TOPIC", "").strip()
    if not topic:
        return "ROOM_NTFY_TOPIC is not set"
    server = os.environ.get("ROOM_NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    cmd = ["curl", "-fsS", "-m", "20", "-o", "/dev/null",
           "-H", f"Title: {title}", "-H", "Priority: high", "-H", "Tags: bell"]
    if click:
        cmd += ["-H", f"Click: {click}"]
    token = os.environ.get("ROOM_NTFY_TOKEN", "").strip()
    if token:
        cmd += ["-H", f"Authorization: Bearer {token}"]
    cmd += ["-d", message, f"{server}/{topic}"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=CURL_TIMEOUT)
    except subprocess.TimeoutExpired:  # its text would hold the whole argv
        return f"curl timed out after {CURL_TIMEOUT}s"
    except OSError as e:  # its text can hold a file name; strerror doesn't
        return f"could not run curl: {e.strerror or type(e).__name__}"
    if r.returncode == 0:
        return None
    err = scrub(r.stderr.strip(), (topic, token)) or f"curl exited {r.returncode}"
    if "429" in err:
        err += " (ntfy's daily limit for this shared IP; a paid ntfy tier plus ROOM_NTFY_TOKEN avoids it)"
    elif "403" in err:
        err += " (is ntfy.sh allowed in this environment's network settings?)"
    return err


def wants_buzz(flag, kind):
    """--buzz or --no-buzz if given, else whether the kind is one that buzzes."""
    return flag if flag is not None else base_kind(kind) in BUZZ_KINDS


def buzz_message(room, role, kind, comment):
    """Buzz about a posted message: its kind, sender and room, never its text."""
    kind = kind or "Message"
    return buzz(f"{kind} · {REPO.split('/')[1]} room {room}", f"{kind} from {role} in {REPO} room {room}",
                comment.get("html_url") or f"https://github.com/{REPO}/issues/{room}")


def buzz_if_wanted(a, kind, comment):
    """After say or close: buzz as the kind and --buzz/--no-buzz say, and print how it went."""
    if wants_buzz(a.buzz, kind):
        err = buzz_message(a.room, a.role, kind, comment)
        # the message is already in the room, so a failed buzz is a warning, not an error
        print("[buzz sent]" if err is None else f"[buzz failed: {err}]")


# --- commands

def cmd_new(a):
    try:  # make sure the label exists; it's fine if it already does
        gh(f"repos/{REPO}/labels", "POST",
           {"name": LABEL, "color": "5319e7", "description": "Agent room: architect + builder"})
    except GhError:
        pass
    body = ("Agent room. Each comment is a message, starting with its sender's role and session.\n\n"
            f"Protocol (agent-room {VERSION}): [architect]({doc_url('ARCHITECT.md')}) · [lead]({doc_url('LEAD.md')})")
    i = gh(f"repos/{REPO}/issues", "POST", {"title": a.title, "body": body, "labels": [LABEL]})
    print(f"room {i['number']} in {REPO}: {i['html_url']}")


def cmd_rooms(a):
    for i in gh(f"repos/{REPO}/issues?state=open&labels={LABEL}&per_page=50"):
        if "pull_request" not in i:
            print(f"{i['number']}\t{i['title']}\t({i['comments']} messages, updated {i['updated_at']})")


def cmd_say(a):
    text = message_text(a.text)
    kind = message_kind(text)
    check_role(a.role, kind)
    lease_guard(a, kind)
    c = post(a.room, a.role, text)
    print(f"sent #{c['id']}")
    buzz_if_wanted(a, kind, c)


def cmd_ping(a):
    err = buzz("agent-room test", "If your phone buzzed, agent-room notifications work.")
    if err:
        sys.exit(f"buzz failed: {err}")
    print("buzz sent - check your phone")


def cmd_read(a):
    if a.all:
        show([parse(c) for c in comments(a.room)])
        return
    if not a.role:
        sys.exit("read needs a ROLE, or --all")
    if a.from_id:
        move_cursor(a.room, a.role, a.from_id)
    new = unseen(a.room, a.role)
    show(new) if new else print("[nothing new]")


def cmd_cursor(a):
    print(cursor_id(a.room, a.role) or "none")


def cmd_wait(a):
    end, polls, fails = time.time() + a.timeout, 0, 0
    while True:
        try:
            new = unseen(a.room, a.role)
            fails = 0
        except GhError as e:
            fails += 1
            print(f"[poll failed ({fails}/10): {e}]", file=sys.stderr)
            if fails >= 10:
                sys.exit(1)
            new = []
        closed = False
        if new or polls % 6 == 0:
            try:
                closed = is_closed(a.room)
            except GhError as e:
                print(f"[state check failed: {e}]", file=sys.stderr)
        if new:
            show(new)
        if closed:
            print("[room is closed]")
            return 4
        if new:
            print(f"[reply: {hint('say', a.room, a.role, ' -')}]")
            print(f"[then re-arm: {hint('wait', a.room, a.role)}]")
            print(f"[cursor: {cursor_id(a.room, a.role)}]")
            return 0
        if time.time() >= end:
            print(f"[no new messages in {a.timeout}s; re-arm: {hint('wait', a.room, a.role)}]")
            return 3
        polls += 1
        time.sleep(a.interval)


def cmd_close(a):
    text = message_text(a.text or "Closing the room.")
    kind = message_kind(text)
    check_role(a.role, kind)
    lease_guard(a, kind)
    # close first, so a waiter woken by the closing note already sees the room as closed
    gh(f"repos/{REPO}/issues/{a.room}", "PATCH", {"state": "closed"})
    c = post(a.room, a.role, text)
    print(f"room {a.room} closed")
    buzz_if_wanted(a, kind, c)


def role_arg(s):
    if not re.fullmatch(r"[a-z][a-z0-9-]*", s) or s == "human":
        raise argparse.ArgumentTypeError("role must be lowercase letters, digits or '-', and not 'human'")
    return s


def repo_arg(s):
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", s):
        raise argparse.ArgumentTypeError("repo must look like OWNER/NAME")
    return s


# --- state branch, lease, preflight
#
# The playbook and pipeline state live on branch agent-room/state of the project repo, under
# docs/playbook/. room.py keeps a git worktree of that branch at $ROOM_STATE_DIR (default
# ~/agent-room-state/OWNER__NAME): `git worktree add` from the project checkout when run inside
# one, else a shallow clone of the branch from $ROOM_STATE_REMOTE (default the GitHub URL).
# Every state write is a push that fails if anyone else pushed first; the lead lease rests on that.
#
#   state init | init-lead | path | sync | commit -m MSG | get KEY | set KEY=VALUE... | next KEY
#   lease take [--takeover] | release | check          preflight --role architect|lead [--fix]
#
# Writes to lead-owned state (state set, state next, state commit of a lead-owned file) need the lease.
# Exit codes: 3 the state branch moved under us (re-read and re-apply), or lease take must stand down;
# 5 the lease is not this session's.

STATE_BRANCH = "agent-room/state"
STATE_REF = f"refs/remotes/origin/{STATE_BRANCH}"
PLAYBOOK_DIR = "docs/playbook"
ARCHITECT_FILES = ("PLAYBOOK.md", "DESIGN.md", "HANDOFF.md")
LEAD_FILES = ("MISSIONS.md", "LEDGER.md", "QODO-VALUE.md")
LEAD_PATHS = {f"{PLAYBOOK_DIR}/{n}" for n in LEAD_FILES}
MISSIONS = f"{PLAYBOOK_DIR}/MISSIONS.md"
LEASE_KEYS = ("lease_session", "lease_generation")
LEASE_HISTORY = 200  # commits of MISSIONS.md walked back to find the last valid block
FENCE = re.compile(r" {0,3}(`{3,}|~{3,})[ \t]*(.*?)[ \t]*")  # a fenced code block's fence line, and its info string
BLOCK_INFO = "agent-room-state"
BLOCK_LINE = re.compile(r"([a-z][a-z0-9_]*):[ \t]*(.*?)[ \t]*")
STATE_KEY = re.compile(r"[a-z][a-z0-9_]*")
TEMPLATE_URL = "https://raw.githubusercontent.com/{repo}/{version}/templates/playbook/{name}"
FIRST_GITIGNORE = "__pycache__/\n*.pyc\n.venv/\nnode_modules/\n.env\n.DS_Store\n"
STATUSES = ("running", "paused", "stopped", "done")  # the machine block's status; a missing one reads as running
STATE_MARKER = "agent-room-state"  # in the git dir of each state worktree room.py makes
EXIT_MOVED, EXIT_LEASE = 3, 5


class StateMoved(Exception):
    """A push to the state branch was rejected because someone else pushed first."""


class BlockUnreadable(StateError):
    """MISSIONS.md, or the machine block in it, is missing or broken (the lease then comes from the
    last valid block in the branch's history: see pushed_lease)."""


class StateExit(Exception):
    """Stop with this exit code and message (5: the lease is someone else's; 3: stand down)."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def identity(cwd):
    """-c options for a commit identity, only where git has none configured."""
    out = []
    for key, value in (("user.name", "agent-room"), ("user.email", "agent-room@users.noreply.github.com")):
        if not git("config", key, cwd=cwd, check=False).stdout.strip():
            out += ["-c", f"{key}={value}"]
    return out


def state_checkout():
    """The project checkout to add the state worktree to (its main worktree), or None to clone instead. Never
    a state clone room.py made, even when run from inside one."""
    if os.environ.get("ROOM_STATE_REMOTE"):
        return None
    here = repo_from_checkout()
    if not here or here.lower() != REPO.lower():
        return None
    common = git("rev-parse", "--git-common-dir", check=False).stdout.strip()
    common = os.path.realpath(common) if common else ""
    if not common or os.path.isfile(os.path.join(common, STATE_MARKER)):
        return None  # inside a state clone: it is no project checkout
    if os.path.basename(common) == ".git":
        return os.path.dirname(common)  # from a linked worktree too, so moving that one aside can't pull the rug
    r = git("rev-parse", "--show-toplevel", check=False)
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def remote_url():
    return os.environ.get("ROOM_STATE_REMOTE") or f"https://github.com/{REPO}.git"


def state_path():
    default = os.path.join("~", "agent-room-state", REPO.replace("/", "__"))
    return os.path.abspath(os.path.expanduser(os.environ.get("ROOM_STATE_DIR") or default))


def state_worktree_exists():
    return os.path.exists(os.path.join(state_path(), ".git"))


def ls_heads(root):
    """{branch: sha} of the project repo's branches, through the checkout ROOT or, if None, remote_url()."""
    out = git("ls-remote", "--heads", "origin", cwd=root).stdout if root else \
        git("ls-remote", "--heads", remote_url()).stdout
    heads = {}
    for line in out.splitlines():
        sha, _, ref = line.partition("\t")
        if ref.startswith("refs/heads/"):
            heads[ref[len("refs/heads/"):]] = sha
    return heads


def remote_heads():
    """{branch: sha} of the project repo's branches."""
    return ls_heads(state_checkout())


# Only a directory room.py made is ever moved aside and rebuilt: it writes STATE_MARKER into the git dir of every
# state worktree or clone it creates (B-2, cold M2 S1-3 to S1-5). A directory whose .git file names an admin dir
# that is gone (the checkout it was added from was cloned again) is the one other case. Anything else is refused,
# whatever the current directory.

def git_dir_of(path):
    """PATH's git dir, read from the file system (PATH/.git, or the gitdir its .git file names) whether or not
    git can open it; None when PATH has no .git."""
    dot = os.path.join(path, ".git")
    if os.path.isdir(dot):
        return dot
    try:
        with open(dot) as f:
            line = f.read().strip()
    except OSError:
        return None
    if not line.startswith("gitdir:"):
        return None
    gd = line[len("gitdir:"):].strip()
    return gd if os.path.isabs(gd) else os.path.normpath(os.path.join(path, gd))


def has_marker(path):
    gd = git_dir_of(path)
    return bool(gd) and os.path.isfile(os.path.join(gd, STATE_MARKER))


def dangling_gitfile(path):
    """PATH's .git is a file naming a git dir that no longer exists."""
    gd = git_dir_of(path)
    return os.path.isfile(os.path.join(path, ".git")) and bool(gd) and not os.path.exists(gd)


def mark(path):
    gd = os.path.join(path, git_out("rev-parse", "--git-dir", cwd=path))
    with open(os.path.join(gd, STATE_MARKER), "w") as f:
        f.write(f"The {STATE_BRANCH} worktree of {REPO}, made by room.py, which may move it aside and rebuild it.\n")


def check_state_dir(path):
    """Fetch, then judge the directory before anything resets or cleans it. Returns 'ok', or 'stale'
    for a state worktree room.py made whose history the recreated branch no longer shares. Refuses
    anything else: a directory with another branch checked out, or with no state history and no marker
    (the project checkout, or a builder's worktree, whatever the current directory)."""
    branch = git("symbolic-ref", "-q", "--short", "HEAD", cwd=path, check=False).stdout.strip()
    if branch and branch != STATE_BRANCH:
        raise StateError(f"{path} has branch {branch} checked out, so it isn't the state worktree; "
                         "set ROOM_STATE_DIR to a directory of its own")
    fetch(path)
    if git("merge-base", "HEAD", STATE_REF, cwd=path, check=False).returncode == 0:
        return "ok"
    if has_marker(path):
        return "stale"
    raise StateError(f"{path} holds no {STATE_BRANCH} history and has no {STATE_MARKER} marker in its git dir "
                     "(the project checkout?), so room.py didn't make it and leaves it alone: move it yourself, or "
                     "set ROOM_STATE_DIR to a directory of its own")


def save_local_work(path, stamp, aside):
    """Before a stale state worktree is moved aside: its HEAD and uncommitted changes as a commit on
    refs/agent-room/broken-<stamp> in its repository (for a linked worktree, the project's, which outlives the
    worktree's own admin dir), else as a patch next to the moved dir. Returns the words for the notice."""
    try:
        head = git_out("rev-parse", "HEAD", cwd=path)
        git("add", "-A", cwd=path)  # its index moves aside with it anyway
        tree = git_out("write-tree", cwd=path)
        snap = head if tree == git_out("rev-parse", "HEAD^{tree}", cwd=path) else git_out(
            *identity(path), "commit-tree", tree, "-p", head, "-m",
            f"agent-room: uncommitted work of the stale state worktree {path}", cwd=path)
        ref = f"refs/agent-room/broken-{stamp}"
        if git("update-ref", ref, snap, "0" * 40, cwd=path, check=False).returncode != 0:  # create, never overwrite
            ref += f"-{os.getpid()}"
            git("update-ref", ref, snap, "0" * 40, cwd=path)
        repo = os.path.realpath(os.path.join(path, git_out("rev-parse", "--git-common-dir", cwd=path)))
        inside = os.path.realpath(path) + os.sep
        if repo.startswith(inside):  # a clone keeps its repo, which moves with it
            repo = os.path.join(aside, repo[len(inside):])
        what = "its HEAD" + (" and uncommitted changes" if snap != head else "")
        return f"saved {what} as {ref} ({snap[:12]}) in {repo}"
    except (StateError, OSError) as e:
        patch = f"{aside}.patch"
        try:
            diff = git("diff", "--cached", "--binary", "HEAD", cwd=path, check=False).stdout
            head = git("rev-parse", "HEAD", cwd=path, check=False).stdout.strip() or "unknown"
            with open(patch, "w") as f:
                f.write(f"HEAD of {path} was {head}; its uncommitted changes follow.\n\n{diff}")
            return f"couldn't save a commit ({e}); saved its HEAD and changes as {patch}"
        except OSError as e2:
            return f"couldn't save its HEAD or changes ({e}; {e2}); its files are in the moved dir"


def move_aside(path, why, save=False):
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    aside = f"{path}.broken-{stamp}"
    if os.path.lexists(aside):
        aside += f"-{os.getpid()}"
    saved = save_local_work(path, stamp, aside) if save else None
    linked = os.path.isfile(os.path.join(path, ".git"))
    os.rename(path, aside)
    if linked:
        # its .git names an admin dir in the project's repo, which the rebuilt worktree at PATH gets after the
        # prune: left in place, git in the moved copy would act on the new worktree. Its work is on the ref.
        os.remove(os.path.join(aside, ".git"))
    print(f"[state worktree {path} {why}; " + (f"{saved}; " if saved else "") + f"moved it to {aside}" +
          (", without its .git link, so it holds plain files," if linked else "") + " and made a new one]",
          file=sys.stderr)


def ensure_worktree():
    """Path of the state worktree, just fetched: checked, rebuilt if broken or stale, created if missing."""
    path = state_path()
    root = state_checkout()  # before anything moves: the current directory may be inside the one moved aside
    if os.path.lexists(os.path.join(path, ".git")):
        r = git("rev-parse", "--show-toplevel", cwd=path, check=False)
        if r.returncode == 0:
            if check_state_dir(path) == "ok":
                return path
            move_aside(path, f"is stale (no history of the recreated {STATE_BRANCH})", save=True)
        elif dangling_gitfile(path) or has_marker(path):
            # e.g. the project checkout it was added from was cloned again
            move_aside(path, "was broken (no git data left to save; its files are kept)")
        elif "not a git repository" in r.stderr:
            raise StateError(f"{path} is no git checkout room.py can open, and has no {STATE_MARKER} marker, so "
                             "room.py leaves it alone: move it yourself, or set ROOM_STATE_DIR")
        else:
            raise StateError(f"git rev-parse in {path}: {r.stderr.strip()}")
    if STATE_BRANCH not in ls_heads(root):
        raise StateError(f"{STATE_BRANCH} doesn't exist in {REPO} yet: the architect runs '{ME} state init'")
    if os.path.isdir(path) and os.listdir(path):
        raise StateError(f"{path} exists and is not a git checkout: move it, or set ROOM_STATE_DIR")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if root:
        git("fetch", "-q", "origin", f"+refs/heads/{STATE_BRANCH}:{STATE_REF}", cwd=root)
        git("worktree", "prune", cwd=root)
        # detached, so two state worktrees of one checkout never share a branch that moves under the other
        git("worktree", "add", "-q", "--detach", path, STATE_REF, cwd=root)
    else:
        git("clone", "-q", "--depth", "1", "--single-branch", "--branch", STATE_BRANCH, remote_url(), path)
    mark(path)
    return path


def fetch(path):
    git("fetch", "-q", "origin", f"+refs/heads/{STATE_BRANCH}:{STATE_REF}", cwd=path)


def pending(path):
    """What the worktree holds beyond the remote branch: '' when nothing."""
    out = []
    if git_out("status", "--porcelain", cwd=path):
        out.append("uncommitted changes")
    if git_out("rev-list", "--count", f"{STATE_REF}..HEAD", cwd=path) != "0":
        out.append("unpushed commits")
    return " and ".join(out)


def reset_to_remote(path):
    git("reset", "-q", "--hard", STATE_REF, cwd=path)
    git("clean", "-q", "-fd", cwd=path)


def sync(path, discard=True):
    """Fetch and reset the worktree to the remote branch. With discard=False, refuse to drop local work."""
    fetch(path)
    if not discard:
        p = pending(path)
        if p:
            raise StateError(f"the state worktree {path} has {p}: push them with '{ME} state commit -m MSG', "
                             f"or drop them with '{ME} state sync'")
    reset_to_remote(path)


def refresh(path):
    """Sync if the worktree holds no local work; otherwise only fetch, and say so."""
    fetch(path)
    p = pending(path)
    if p:
        print(f"[state worktree has {p}; not synced]", file=sys.stderr)
    else:
        reset_to_remote(path)


def is_ancestor(path, a, b):
    return git("merge-base", "--is-ancestor", a, b, cwd=path, check=False).returncode == 0


def commit_and_push(path, msg):
    """Commit everything in the worktree and push it. Returns False when there was nothing to push.

    Raises StateMoved, with the worktree reset to the remote, if the branch moved under the work."""
    git("add", "-A", cwd=path)
    staged = git("diff", "--cached", "--quiet", cwd=path, check=False)
    if staged.returncode not in (0, 1):  # 0: nothing staged, 1: changes; anything else is git failing
        raise StateError(f"git diff: {(staged.stderr or staged.stdout).strip() or f'exited {staged.returncode}'}")
    if staged.returncode == 1:
        git(*identity(path), "commit", "-q", "-m", msg, cwd=path)
    if git_out("rev-list", "--count", f"{STATE_REF}..HEAD", cwd=path) == "0":
        return False  # no local commits; the remote may be ahead, which is not ours to push
    head = git_out("rev-parse", "HEAD", cwd=path)
    # the commit the work was built on: the new commit's parent, or the first of several unpushed ones.
    # Taken from history, not from the tracking ref, which any fetch (lease check, git fetch) moves.
    base = git_out("merge-base", "HEAD", STATE_REF, cwd=path)
    r = git("push", "-q", "origin", f"HEAD:refs/heads/{STATE_BRANCH}", cwd=path, check=False)
    if r.returncode == 0:
        git("update-ref", STATE_REF, head, cwd=path)
        return True
    fetch(path)
    remote = git_out("rev-parse", STATE_REF, cwd=path)
    if is_ancestor(path, head, remote):
        return True  # the push landed and only its acknowledgement was lost
    if remote != base:
        reset_to_remote(path)
        raise StateMoved()
    raise StateError(f"git push: {(r.stderr or r.stdout).strip()}")


def push_new_branch(branch, files, msg):
    """Push a root commit holding files {path: text} as a new branch. False if the branch appeared meanwhile."""
    root = state_checkout()
    with tempfile.TemporaryDirectory() as t:
        git("init", "-q", t)
        for rel, text in files.items():
            os.makedirs(os.path.dirname(os.path.join(t, rel)), exist_ok=True)
            with open(os.path.join(t, rel), "w") as f:
                f.write(text)
        git("add", "-A", cwd=t)
        git(*identity(t), "commit", "-q", "-m", msg, cwd=t)
        if root:  # push through the checkout, so it uses the checkout's remote and credentials
            sha = git_out("rev-parse", "HEAD", cwd=t)
            git("fetch", "-q", t, "HEAD", cwd=root)
            r = git("push", "-q", "origin", f"{sha}:refs/heads/{branch}", cwd=root, check=False)
        else:
            r = git("push", "-q", remote_url(), f"HEAD:refs/heads/{branch}", cwd=t, check=False)
    if r.returncode == 0:
        return True
    if branch in remote_heads():
        return False
    raise StateError(f"git push {branch}: {(r.stderr or r.stdout).strip()}")


def template(name):
    """A playbook template: from templates/playbook/ beside this file, else downloaded at VERSION."""
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "playbook", name)
    if os.path.isfile(local):
        with open(local) as f:
            return f.read()
    url = TEMPLATE_URL.format(repo=HOME_REPO, version=VERSION, name=name)
    try:
        r = subprocess.run(["curl", "-fsSL", "-m", "30", url], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise StateError(f"downloading {url}: {e}")
    if r.returncode != 0 or not r.stdout.strip():
        raise StateError(f"downloading {url}: {r.stderr.strip() or 'empty response'}")
    return r.stdout


def render(name):
    text = template(name)
    if name == "PLAYBOOK.md":
        text = re.sub(r"^pipeline:.*$", f"pipeline: {VERSION}", text, count=1, flags=re.M)
        text = re.sub(r"^repo:.*$", f"repo: {REPO}", text, count=1, flags=re.M)
    return text


def add_missing(names, msg):
    """Sync, add the named playbook files that are missing, commit and push. Returns (path, added)."""
    path = ensure_worktree()
    sync(path, discard=False)
    missing = [n for n in names if not os.path.exists(os.path.join(path, PLAYBOOK_DIR, n))]
    texts = {n: render(n) for n in missing}  # render all first, so a failed download writes nothing
    if "MISSIONS.md" in texts:
        values, _ = pushed_lease(path)
        if values:  # deleted outside room.py: carry the last valid block, so no generation or counter repeats
            texts["MISSIONS.md"] = with_block(texts["MISSIONS.md"], values)
    for n, text in texts.items():
        os.makedirs(os.path.join(path, PLAYBOOK_DIR), exist_ok=True)
        with open(os.path.join(path, PLAYBOOK_DIR, n), "w") as f:
            f.write(text)
    if missing:
        commit_and_push(path, f"{msg}: {', '.join(missing)}")
    return path, missing


# The machine block of MISSIONS.md, parsed strictly (B-3, cold M2 S3-1 to S3-3): it is the first fenced block
# in the file and the only one whose info string is agent-room-state; its body is only `key: value` and blank
# lines, each key once; a bare fence line closes it. Anything else makes it invalid, and the lease then comes
# from the last commit whose block is valid (pushed_lease).

def fenced_blocks(lines):
    """[(open, close or None, info)] of the fenced code blocks in LINES, by line index, in order."""
    out, cur = [], None
    for i, line in enumerate(lines):
        m = FENCE.fullmatch(line.rstrip("\r"))
        if cur is None:
            if m:
                cur = (i, m.group(1), m.group(2))
        elif m and m.group(1)[0] == cur[1][0] and len(m.group(1)) >= len(cur[1]) and not m.group(2):
            out.append((cur[0], i, cur[2]))
            cur = None
    if cur:
        out.append((cur[0], None, cur[2]))
    return out


def locate_block(text):
    """(open, close, values) of the machine block in MISSIONS.md TEXT, by line index. Raises BlockUnreadable,
    saying why, unless the block is valid."""
    lines = text.split("\n")
    blocks = fenced_blocks(lines)
    ours = [b for b in blocks if b[2] == BLOCK_INFO]
    if not ours:
        raise BlockUnreadable(f"{MISSIONS} has no {BLOCK_INFO} block")
    if len(ours) > 1:
        raise BlockUnreadable(f"{MISSIONS} has {len(ours)} {BLOCK_INFO} blocks, and may have only one")
    start, end, _ = ours[0]
    if blocks[0] != ours[0]:
        raise BlockUnreadable(f"{MISSIONS}'s {BLOCK_INFO} block isn't its first fenced block")
    if end is None:
        raise BlockUnreadable(f"{MISSIONS}'s {BLOCK_INFO} block has no closing fence")
    values = {}
    for line in lines[start + 1:end]:
        if not line.strip():
            continue
        m = BLOCK_LINE.fullmatch(line.rstrip("\r"))
        if not m:
            raise BlockUnreadable(f"{MISSIONS}'s {BLOCK_INFO} block has a line that isn't `key: value`: {line[:60]!r}")
        if m.group(1) in values:
            raise BlockUnreadable(f"{MISSIONS}'s {BLOCK_INFO} block sets {m.group(1)} twice")
        values[m.group(1)] = m.group(2)
    return start, end, values


def read_block(text):
    return locate_block(text)[2]


def write_block(text, updates):
    """TEXT with the valid machine block's keys set from UPDATES (new keys appended), all else untouched."""
    start, end, _ = locate_block(text)
    lines = text.split("\n")
    body, done = [], set()
    for line in lines[start + 1:end]:
        m = BLOCK_LINE.fullmatch(line.rstrip("\r"))
        if m and m.group(1) in updates:
            body.append(f"{m.group(1)}: {updates[m.group(1)]}")
            done.add(m.group(1))
        else:
            body.append(line)
    body += [f"{k}: {v}" for k, v in updates.items() if k not in done]
    return "\n".join(lines[:start + 1] + body + lines[end:])


def render_block(values):
    return f"```{BLOCK_INFO}\n" + "".join(f"{k}: {v}\n" for k, v in values.items()) + "```\n"


def with_block(text, values):
    """MISSIONS.md TEXT (None if missing: the template) with its machine block holding VALUES: updated in
    place if valid. Otherwise nothing is deleted: every fence whose info string starts with agent-room-state
    is renamed to agent-room-state-damaged, and a fresh block goes first, under the title."""
    if text is None:
        text = template("MISSIONS.md")
    try:
        return write_block(text, values)
    except BlockUnreadable:
        pass
    lines = text.split("\n")
    for i, line in enumerate(lines):
        m = FENCE.fullmatch(line.rstrip("\r"))
        if m and re.match(rf"{BLOCK_INFO}(?![\w-])", m.group(2)):
            lines[i] = line.replace(BLOCK_INFO, f"{BLOCK_INFO}-damaged", 1)
    text = "\n".join(lines)
    block = render_block(values)
    first, _, rest = text.partition("\n")
    if first.startswith("# "):
        return f"{first}\n\n{block}\n" + rest.lstrip("\n")
    return f"{block}\n{text}"


def missions_text(path):
    f = os.path.join(path, PLAYBOOK_DIR, "MISSIONS.md")
    if not os.path.isfile(f):
        raise StateError(f"{PLAYBOOK_DIR}/MISSIONS.md is missing: the lead runs '{ME} state init-lead'")
    with open(f) as fh:
        return fh.read()


def lease_of(values):
    return values.get("lease_session", "none") or "none", values.get("lease_generation", "0")


def require_lease(values, sid, doing="not written"):
    """Raise exit 5 unless SID holds the lease in VALUES (a machine block)."""
    holder, gen = lease_of(values)
    if holder == sid:
        return
    who = "no session holds the lease" if holder == "none" else \
        f"the lease is held by {holder} (generation {gen}), not this session ({sid})"
    raise StateExit(EXIT_LEASE, f"{doing}: {who}; see '{ME} lease check'")


def change_state(a, msg, fn, need_lease=True):
    """Sync, read the lease (the last valid block, see pushed_lease), check that this session holds it
    (unless need_lease is False), apply fn(values) -> {key: value}, and write the whole block back,
    which restores it if the pushed one is damaged or gone. Commit and push. Returns the updates."""
    path = ensure_worktree()
    sync(path, discard=False)
    f = os.path.join(path, MISSIONS)
    text = open(f).read() if os.path.isfile(f) else None
    values, note = pushed_lease(path)
    if text is None and not values:
        raise StateError(f"{MISSIONS} is missing: the lead runs '{ME} state init-lead'")
    if need_lease:
        require_lease(values, session_id(a))
    updates = fn(values)
    moved = [k for k in ("step", "pr") if k in updates and updates[k] != values.get(k)]
    if moved and "waiting_for_owner" not in updates and (values.get("waiting_for_owner") or "no").strip().lower() != "no":
        # the wait is over once the step or the pr moves (merge records pr), unless this write says otherwise
        updates = {**updates, "waiting_for_owner": "no"}
        print(f"[waiting_for_owner set back to no: the {' and the '.join(moved)} moved]", file=sys.stderr)
    if note:
        print(f"[{note}; this write restores it]", file=sys.stderr)
    with open(f, "w") as fh:
        fh.write(with_block(text, {**values, **updates}))
    commit_and_push(path, msg + (" (restores the machine block)" if note else ""))
    return updates


def pushed_text(path, name, ref=STATE_REF):
    """A playbook file as last fetched from the state branch (or at REF), or None if it isn't there."""
    r = git("show", f"{ref}:{PLAYBOOK_DIR}/{name}", cwd=path, check=False)
    return r.stdout if r.returncode == 0 else None


def pushed_lease(path):
    """The lease: the machine block of the most recent state-branch commit whose MISSIONS.md block
    parses, walking back at most LEASE_HISTORY commits of MISSIONS.md. Returns (values, note): values
    is {} when no block parses, which means no session holds the lease; note is None when the pushed
    tip's own block parses, else a line for a warning. A damaged block never frees the lease, and
    nothing outside the block (a quoted line, say) can decide it."""
    text = pushed_text(path, "MISSIONS.md")
    if text is not None:
        try:
            return read_block(text), None
        except BlockUnreadable:
            pass
    what = f"{MISSIONS} is missing" if text is None else f"{MISSIONS} has no valid agent-room-state block"
    if git_out("rev-parse", "--is-shallow-repository", cwd=path) == "true":  # a clone of depth 1
        git("fetch", "-q", f"--depth={LEASE_HISTORY}", "origin", f"+refs/heads/{STATE_BRANCH}:{STATE_REF}",
            cwd=path, check=False)
    for sha in git_out("log", "--format=%H", "-n", str(LEASE_HISTORY), STATE_REF, "--", MISSIONS, cwd=path).split():
        old = pushed_text(path, "MISSIONS.md", sha)
        try:
            values = read_block(old) if old is not None else None
        except BlockUnreadable:
            values = None
        if values is not None:
            return values, f"{what} on {STATE_BRANCH}; the lease is read from {sha[:7]}, its last valid block"
    return {}, f"{what} on {STATE_BRANCH}, and no earlier commit has a valid one: no session holds the lease"


def pushed_state():
    """(worktree path, machine block, note) on the freshly fetched state branch: the pushed block, else the
    last valid one (see pushed_lease), and a note saying so; the block is {} when none parses. Reads git
    objects only, so local work in the worktree is neither used nor touched."""
    path = ensure_worktree()  # fetched
    values, note = pushed_lease(path)
    return path, values, note


def recorded_state():
    """(path, block) from pushed_state for commands that only read it: a note goes to stderr, and no valid
    block anywhere in the history is an error."""
    path, values, note = pushed_state()
    if not values:
        raise BlockUnreadable(f"{note}: the lead runs '{ME} state init-lead'")
    if note:
        print(f"[{note}]", file=sys.stderr)
    return path, values


def lease_holder():
    """(session, generation, note) of the lease on the freshly fetched state branch (see pushed_lease)."""
    _, values, note = pushed_state()
    holder, gen = lease_of(values)
    return holder, gen, note


def lease_guard(a, kind=None):
    """Lease check on send, for say and close: a lead with a state worktree may not post while
    another session holds the lease (exit 5). A released lease (none) doesn't block, so a
    retiring lead can still post NEXT-LEAD-NEEDED. While the pushed block is damaged, the last valid
    one decides (with a warning), so its holder can still report the problem. No kind is exempt;
    KIND is unused."""
    if a.role != "lead" or not state_worktree_exists():
        return
    sid = session_id(a)
    try:
        holder, gen, note = lease_holder()
    except StateError as e:
        sys.exit(f"not sent: lease check failed: {e}")
    if note:
        print(f"[{note}]", file=sys.stderr)
    if holder not in (sid, "none"):
        print(f"not sent: the lease is held by {holder} (generation {gen}), not this session ({sid})",
              file=sys.stderr)
        sys.exit(EXIT_LEASE)


# --- state, lease and preflight commands

def cmd_state_init(a):
    heads = remote_heads()
    # templates first, so a failed download changes nothing
    files = {} if STATE_BRANCH in heads else {f"{PLAYBOOK_DIR}/{n}": render(n) for n in ARCHITECT_FILES}
    if "main" not in heads:
        others = sorted(h for h in heads if h != STATE_BRANCH)
        if others:
            raise StateError(f"{REPO} has no main branch but has {', '.join(others)}; agent-room builds on main")
        if push_new_branch("main", {"README.md": f"# {REPO.split('/')[1]}\n", ".gitignore": FIRST_GITIGNORE},
                           "Initial commit"):
            print(f"created main in {REPO} with a first commit")
    if files:
        if push_new_branch(STATE_BRANCH, files, "agent-room: start the playbook from templates"):
            print(f"created {STATE_BRANCH} with {', '.join(ARCHITECT_FILES)}")
    path, added = add_missing(ARCHITECT_FILES, "agent-room: add missing architect files")
    if added:
        print(f"added {', '.join(added)}")
    print(f"state branch ready: {path}")


def cmd_state_init_lead(a):
    path, added = add_missing(LEAD_FILES, "agent-room: add lead files")
    print(f"added {', '.join(added)}" if added else "lead files already present")
    print(f"state branch ready: {path}")


def cmd_state_path(a):
    path = ensure_worktree()
    refresh(path)
    print(path)


def cmd_state_sync(a):
    path = ensure_worktree()
    sync(path)
    print(f"synced {path} to {STATE_BRANCH} at {git_out('rev-parse', '--short', 'HEAD', cwd=path)}")


def changed_paths(path):
    """Paths the worktree changes against the commit its work was built on: staged and unpushed.
    Without rename detection, so a renamed or moved file counts under its old name too."""
    git("add", "-A", cwd=path)
    out = set(git_out("diff", "--cached", "--no-renames", "--name-only", cwd=path).splitlines())
    base = git("merge-base", "HEAD", STATE_REF, cwd=path, check=False).stdout.strip()
    if base:
        out |= set(git_out("diff", "--no-renames", "--name-only", base, "HEAD", cwd=path).splitlines())
    return out


def check_missions(path, current):
    """Refuse (exit 1) a MISSIONS.md that loses its valid block or changes the lease by hand: only
    lease take, lease release and room.py's own writes change lease_session and lease_generation."""
    f = os.path.join(path, MISSIONS)
    why = "it would change the lease"
    try:
        new = read_block(open(f).read()) if os.path.isfile(f) else None
        if new is None:
            why = "it would be gone"
    except BlockUnreadable as e:
        new, why = None, str(e)
    if new is None or lease_of(new) != lease_of(current):
        holder, gen = lease_of(current)
        raise StateError(f"not committed: MISSIONS.md must keep a valid agent-room-state block with the current "
                         f"lease (lease_session: {holder}, lease_generation: {gen}), and {why}; only 'lease take' "
                         "and 'lease release' change the lease")


def cmd_state_commit(a):
    path = ensure_worktree()
    changed = changed_paths(path)
    touched = sorted(changed & LEAD_PATHS)
    if touched:  # lead-owned files need the lease, read from the freshly fetched branch
        fetch(path)
        values, note = pushed_lease(path)
        require_lease(values, session_id(a), f"not committed ({', '.join(touched)} are lead-owned)")
        if MISSIONS in changed:
            check_missions(path, values)
        elif note:
            print(f"[{note}; the holder's next state write restores it]", file=sys.stderr)
    if commit_and_push(path, a.message):
        print(f"pushed {git_out('rev-parse', '--short', 'HEAD', cwd=path)} to {STATE_BRANCH}")
    else:
        print("nothing to commit")


def cmd_state_get(a):
    path = ensure_worktree()
    refresh(path)
    try:
        values = read_block(missions_text(path))
    except BlockUnreadable:
        values, note = pushed_lease(path)  # the last valid block
        print(f"[{note}]", file=sys.stderr)
    if a.key not in values:
        raise StateError(f"no key '{a.key}' in the state block")
    print(values[a.key])


def single_line(key, value):
    """VALUE stripped, or StateError if it holds any break read_block's splitlines() honours."""
    if f"x{value}x".splitlines() != [f"x{value}x"]:
        raise StateError(f"the value of {key} must be a single line (no line or paragraph separators)")
    return value.strip()


def cmd_state_set(a):
    updates = {}
    for pair in a.pairs:
        key, sep, value = pair.partition("=")
        if not sep or not STATE_KEY.fullmatch(key):
            raise StateError(f"expected KEY=VALUE with a lowercase key, got {pair!r}")
        value = single_line(key, value)
        if key in LEASE_KEYS:
            raise StateError(f"{key} changes only through 'lease take' and 'lease release'")
        if key == "status" and value not in STATUSES:
            raise StateError(f"status must be one of {', '.join(STATUSES)}, not {value!r}")
        if key == "mission_started" and value != "none" and parse_time(value) is None:
            raise StateError(f"mission_started must be an ISO-8601 UTC time such as {iso(time.time())}, or none")
        updates[key] = value
    change_state(a, f"state: set {', '.join(updates)}", lambda values: updates)
    print("set " + " ".join(f"{k}={v}" for k, v in updates.items()))


def next_int(values, key):
    try:
        return str(int(values.get(key) or "0") + 1)
    except ValueError:
        raise StateError(f"{key} is {values[key]!r}, not a number")


def cmd_state_next(a):
    if not STATE_KEY.fullmatch(a.key):
        raise StateError(f"bad key {a.key!r}")
    if a.key in LEASE_KEYS:
        raise StateError(f"{a.key} changes only through 'lease take' and 'lease release'")
    print(change_state(a, f"state: next {a.key}", lambda v: {a.key: next_int(v, a.key)})[a.key])


def cmd_lease_take(a):
    sid = session_id(a)
    seen = []  # the lease as each try found it

    def take(values):
        holder, gen = lease_of(values)
        seen.append((holder, gen))
        if holder not in ("none", sid) and not a.takeover:
            raise StateExit(EXIT_MOVED, f"lease held by {holder}: stand down (generation {gen}; "
                                        "--takeover only for a lead Matthew starts once the architect finds the old lead gone)")
        # a lead that takes the lease is running: a status left at paused, stopped or done mustn't mute the watchdog.
        # waiting_for_owner stays: a successor may join while the owner still hasn't answered, and a stale flag is
        # ended by a step or pr change, and doesn't mute the watchdog once anything has progressed since it was set
        return {"lease_session": sid, "lease_generation": next_int(values, "lease_generation"), "status": "running"}

    for _ in range(2):
        try:
            new = change_state(a, f"lease: {sid} takes the lead lease", take, need_lease=False)
            print(new["lease_generation"])
            return 0
        except StateMoved:
            # the push lost to some other write; only a lease that another session took means stand down
            holder, gen, _ = lease_holder()
            if holder not in ("none", sid) and (holder, gen) != seen[-1]:
                print(f"lease not taken: {holder} took it first (generation {gen}); stand down", file=sys.stderr)
                return EXIT_MOVED
    print(f"lease not taken: {STATE_BRANCH} moved under both tries, and no session took the lease; "
          "run 'lease take' again", file=sys.stderr)
    return 1


def cmd_lease_release(a):
    sid = session_id(a)
    try:
        change_state(a, f"lease: {sid} releases the lead lease", lambda v: {"lease_session": "none"})
    except StateMoved:
        print("lease not released: the state branch moved; see 'lease check'", file=sys.stderr)
        return EXIT_MOVED
    print(f"lease released by {sid}")


def cmd_lease_check(a):
    sid = session_id(a)
    holder, gen, note = lease_holder()
    if note:
        print(f"[{note}]", file=sys.stderr)
    if holder == sid:
        print(f"lease held by this session ({sid}, generation {gen})")
        return 0
    print(f"lease held by {holder} (generation {gen}), not this session ({sid})")
    return EXIT_LEASE


def gh_try(path):
    """(200, body), or (HTTP status from gh's error or 0, message)."""
    try:
        return 200, gh(path)
    except GhError as e:
        m = re.search(r"HTTP (\d{3})", str(e))
        return (int(m.group(1)) if m else 0), str(e)


def unprotected(status, msg):
    # 404: no protection; 403 "upgrade": a private repo on GitHub Free, which can't have any
    return status == 404 or (status == 403 and "upgrad" in msg.lower())


def cmd_preflight(a):
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except AttributeError:
        pass
    architect = a.role == "architect"
    marks = []

    def check(mark, text):
        marks.append(mark)
        print(f"{mark} {text}", flush=True)

    # push access, and the repo settings read with it
    status, repo = gh_try(f"repos/{REPO}")
    if status != 200:
        check("✗", f"push access: can't read {REPO}: {repo}")
        repo = None
    elif (repo.get("permissions") or {}).get("push"):
        check("✓", f"push access to {REPO}")
    else:
        check("✗", f"push access: this account can't push to {REPO}; approve repo access, and make sure no "
                   f"ruleset covers mission/*, task branches or {STATE_BRANCH}")

    # main has commits
    heads = None
    try:
        heads = remote_heads()
    except StateError as e:
        check("✗", f"main has commits: can't list branches: {e}")
    if heads is not None:
        if "main" in heads:
            check("✓", "main has commits")
        else:
            check("✗", "main has no commits: " + (f"run '{ME} state init'" if architect
                                                  else "the architect's kickoff ('state init') creates the first commit"))

    # approving reviews on main, in classic protection or rules
    errors, notes, where = [], [], []
    status, classic = gh_try(f"repos/{REPO}/branches/main/protection")
    if status != 200:
        if not unprotected(status, classic):
            errors.append(f"classic protection: {classic}")
        elif status == 403:
            notes.append("private repo on GitHub Free: no protection possible")
        classic = None
    status, rules = gh_try(f"repos/{REPO}/rules/branches/main")
    if status != 200 or not isinstance(rules, list):
        if status != 200 and not unprotected(status, rules):
            errors.append(f"rules: {rules}")
        rules = []
    rulesets, unread = {}, []  # unread: rulesets whose details couldn't be read, so their bypass is unknown
    for rule in rules:
        rid = rule.get("ruleset_id")
        if rid is not None and rid not in rulesets:
            s, rs = gh_try(f"repos/{REPO}/rulesets/{rid}")
            rulesets[rid] = rs if s == 200 and isinstance(rs, dict) else {}
            if not (s == 200 and isinstance(rs, dict)):
                unread.append(rid)

    def ruleset_name(rid, rule=None):
        name = rulesets.get(rid, {}).get("name")
        src = (rule or {}).get("ruleset_source") or ""
        return f"ruleset '{name}' (id {rid})" if name else f"ruleset {rid}" + (f" from {src}" if src else "")

    if classic:
        n = (classic.get("required_pull_request_reviews") or {}).get("required_approving_review_count") or 0
        if n:
            where.append(f"classic branch protection ({n} approving)")
    for rule in rules:
        if rule.get("type") == "pull_request":
            n = (rule.get("parameters") or {}).get("required_approving_review_count") or 0
            if n:
                where.append(f"{ruleset_name(rule.get('ruleset_id'), rule)} ({n} approving)")
    if errors:
        check("✗", "approving reviews: can't read the rules for main: " + "; ".join(errors))
    elif where:
        check("✗", "main requires approving reviews in " + ", ".join(where) + "; remove only that rule, "
                   "keep required status checks and force-push protection")
    else:
        check("✓", "main requires no approving reviews" + (f" ({'; '.join(notes)})" if notes else ""))

    # admin bypass: report only
    bypass = []
    if classic and not (classic.get("enforce_admins") or {}).get("enabled"):
        bypass.append("admins can bypass classic protection (enforce_admins off)")
    for rid, rs in rulesets.items():
        actors = rs.get("bypass_actors") or []
        if actors:
            who = ", ".join(f"{x.get('actor_type', '?')} {x.get('actor_id', '')}".strip() for x in actors)
            bypass.append(f"{ruleset_name(rid)} has bypass actors: {who}")
    bypass += [f"couldn't read ruleset {rid}, so its bypass actors are unknown" for rid in unread]
    if bypass:
        check("!", "admin bypass: " + "; ".join(bypass) + " (report only: the lead never pushes to main)")
    elif errors:
        check("!", "admin bypass: unknown, the rules for main couldn't be read (report only)")
    elif not classic and not rules:
        check("!", "admin bypass: main has no protection or rules, so anyone with push access can push to it "
                   "(report only: the lead never pushes to main)")
    else:
        check("✓", "admin bypass: none")

    # automatic deletion of merged head branches (agents can't delete branches themselves)
    if repo is not None:
        dbm = repo.get("delete_branch_on_merge")
        if dbm is True:
            check("✓", "merged head branches are deleted automatically")
        else:
            check("!", ("couldn't read delete_branch_on_merge; " if dbm is None else "") +
                  "Matthew: turn on 'Automatically delete head branches' (repo Settings > General > "
                  "Pull Requests), so merged mission branches are removed")

    # merge commits allowed: `merge` uses merge_method=merge, which GitHub refuses when they are off
    if repo is not None:
        amc = repo.get("allow_merge_commit")
        why = "(repo Settings > General > Pull Requests), because 'merge' uses a merge commit"
        if amc is True:
            check("✓", "merge commits are allowed")
        elif amc is False:
            check("✗", f"merge commits are not allowed: Matthew: turn on 'Allow merge commits' {why}")
        else:
            check("!", f"couldn't read allow_merge_commit; Matthew: check that 'Allow merge commits' is on {why}")

    # the state branch, with the architect's files and a pinned version: read from the pushed
    # branch after a fetch, so uncommitted edits in the worktree can't pass for it
    path = None
    try:
        path = ensure_worktree()  # fetched
    except StateError as e:
        path = None
        check("✗", f"state branch: {e}")
    if path:
        missing = [n for n in ("PLAYBOOK.md", "DESIGN.md") if pushed_text(path, n) is None]
        who = "" if architect else " (the architect)"
        if missing:
            fix = f"run '{ME} state init'" if architect else "the architect commits them"
            check("✗", f"state branch lacks {', '.join(missing)}: {fix}")
        else:
            m = re.search(r"^pipeline:[ \t]*(\S*)", pushed_text(path, "PLAYBOOK.md"), re.M)
            value = m.group(1) if m else ""
            if not value:
                check("✗", f"state branch: PLAYBOOK.md has no pipeline version: add `pipeline: vX.Y.Z` to "
                           f"PLAYBOOK.md{who}")
            elif re.fullmatch(r"v\d+(\.\d+)*(-[\w.]+)?", value) and pin_rejected(value):
                check("✗", f"state branch: {pin_rejected(value)}{who}")  # a pre-release pin (cold M6b R1-6)
            elif re.fullmatch(r"v\d+(\.\d+)*(-[\w.]+)?", value):
                check("✓", f"state branch has PLAYBOOK.md and DESIGN.md, pinned to {value}")
            elif value == "main":
                check("!", "state branch has PLAYBOOK.md and DESIGN.md, but the pipeline is 'main', "
                           "not a release tag (fine while agent-room itself is in development)")
            else:
                check("✗", f"state branch: PLAYBOOK.md pins the pipeline to '{value}', not a release tag: "
                           f"make it `pipeline: vX.Y.Z`{who}")

    # the lead task (M6b): the lead starts its successor through it. The architect's chat doesn't have the
    # environment's variables, so it checks only the lead-task: line. The token is never printed
    if path:
        task = lead_task_id(pushed_text(path, "PLAYBOOK.md"))
        token = None if architect else fire_token()
        if task and (architect or token):
            check("✓", f"lead task {task} is set in PLAYBOOK.md" if architect else f"lead task {task} and its token are set")
        else:
            missing = ([] if task else ["no lead-task: line in PLAYBOOK.md"]) + \
                ([] if architect or token else [f"neither {fire_token_var()} nor ROOM_FIRE_TOKEN is set"])
            check("!", f"lead task not configured: a handover will post NEXT-LEAD-NEEDED ({'; '.join(missing)})")
    else:
        check("!", f"lead task: can't check without {STATE_BRANCH}")

    if not architect:
        # lead-owned files
        if not path:
            check("✗", "lead-owned files: can't check without the state branch")
        else:
            missing = [n for n in LEAD_FILES if pushed_text(path, n) is None]
            if missing and a.fix:
                try:
                    path, added = add_missing(LEAD_FILES, "agent-room: add lead files")
                    check("✓", f"lead-owned files exist (--fix created {', '.join(added) or 'none'})")
                except (StateError, StateMoved) as e:
                    why = str(e) or "the state branch moved; run it again"  # an exception is truthy even when empty
                    check("✗", f"lead-owned files: --fix failed: {why}")
            elif missing:
                check("✗", f"lead-owned files missing: {', '.join(missing)}: run '{ME} state init-lead', "
                           "or preflight --fix")
            else:
                try:
                    read_block(pushed_text(path, "MISSIONS.md"))
                    check("✓", "lead-owned files exist")
                except StateError as e:
                    check("✗", f"lead-owned files: {e}; the lease holder's next state write restores it "
                               "('lease take --takeover' if the holder is gone)")
        # environment
        if os.environ.get("ROOM_NTFY_TOPIC", "").strip():
            check("✓", "ROOM_NTFY_TOPIC is set")
        else:
            check("✗", "ROOM_NTFY_TOPIC is not set: add it to the agent-room environment")
        q = os.environ.get("QODO_REVIEW", "").strip()
        if q in ("on", "off"):
            check("✓", f"QODO_REVIEW is {q}")
        else:
            check("✗", f"QODO_REVIEW must be 'on' or 'off', not {q!r}: set it in the agent-room environment")

    fails, warns = marks.count("✗"), marks.count("!")
    print(f"preflight {'failed' if fails else 'passed'}: {fails} failed, {warns} warning(s)")
    return 1 if fails else 0


def state_command(fn):
    def run(a):
        try:
            return fn(a)
        except StateMoved:
            print("state moved: run 'state sync', re-read, re-apply", file=sys.stderr)
            return EXIT_MOVED
        except StateExit as e:
            print(e, file=sys.stderr)
            return e.code
        except StateError as e:
            sys.exit(str(e))
    return run


def add_state_commands(sub, common):
    """argparse wiring for state, lease and preflight (options go after the leaf command)."""
    def leaf(group, name, fn, help):
        s = group.add_parser(name, parents=[common], help=help, description=help)
        s.set_defaults(fn=state_command(fn))
        return s

    st = sub.add_parser("state", help=f"the playbook and pipeline state on {STATE_BRANCH}")
    ss = st.add_subparsers(dest="state_cmd", required=True)
    leaf(ss, "init", cmd_state_init, "architect: first commit on an empty main, state branch from templates")
    leaf(ss, "init-lead", cmd_state_init_lead, "lead: add missing lead-owned files from templates")
    leaf(ss, "path", cmd_state_path, "print the state worktree's path, creating or syncing it first")
    leaf(ss, "sync", cmd_state_sync, f"fetch and hard-reset the worktree to origin/{STATE_BRANCH}")
    s = leaf(ss, "commit", cmd_state_commit, "commit all changes in the worktree and push (lead-owned files need "
             "the lease, exit 5; exit 3 if the branch moved)")
    s.add_argument("-m", dest="message", required=True)
    leaf(ss, "get", cmd_state_get, "print a value from the machine block of MISSIONS.md").add_argument("key")
    s = leaf(ss, "set", cmd_state_set, "sync, set values, commit and push (needs the lease, exit 5; exit 3 on a "
             "lost race)")
    s.add_argument("pairs", nargs="+", metavar="KEY=VALUE")
    s = leaf(ss, "next", cmd_state_next, "increment a counter, push, print the new value (needs the lease)")
    s.add_argument("key")

    ls = sub.add_parser("lease", help="the lead lease in MISSIONS.md")
    lss = ls.add_subparsers(dest="lease_cmd", required=True)
    s = leaf(lss, "take", cmd_lease_take, "take the lead lease: next generation, this session (exit 3 if another "
             "session holds it or pushed first)")
    s.add_argument("--takeover", action="store_true",
                   help="take it even from another session: only for a lead Matthew starts once the architect finds the old lead gone")
    leaf(lss, "release", cmd_lease_release, "the holder sets the lease to none (at HANDOFF, PAUSED, STOPPED, DONE)")
    leaf(lss, "check", cmd_lease_check, "exit 0 if this session holds the lease, else 5")

    s = leaf(sub, "preflight", cmd_preflight, "check the repo, the state branch and the environment")
    s.add_argument("--role", choices=("architect", "lead"), required=True)
    s.add_argument("--fix", action="store_true", help="lead: create missing lead-owned files")


# --- end of state branch, lease, preflight


def add_buzz_flags(s):
    g = s.add_mutually_exclusive_group()
    g.add_argument("--buzz", dest="buzz", action="store_const", const=True, default=None,
                   help="push a phone notification via ntfy even if the kind doesn't buzz")
    g.add_argument("--no-buzz", dest="buzz", action="store_const", const=False,
                   help="no phone notification, even if the kind buzzes")


# --- review records, merge gate and merge
#
# Review records travel with the code on the mission branch, under reviews/. Only the record files
# below are exempt from the coverage rule (deferral B-1): anything else under reviews/ is a change
# that needs a review like any other. Formats: docs/design/m3-reviews-gate.md, "Review records".
#
#   gate PR [--mission M<k>] [--allow-hold 5 --decision DECISION-<n>]
#   merge PR --sha SHA [--mission M<k>] [--allow-hold 5 --decision DECISION-<n>]
#
# Exit codes: 0 pass (or merged), 3 wait (checks pending, or the head moved), 5 lease lost,
# 6 fail (hold reasons) or not mergeable, 1 errors.

EXIT_WAIT, EXIT_FAIL = 3, 6
REVIEW_EXEMPT = tuple(re.compile(p) for p in (
    r"reviews/cold/M\d+/round-\d+\.md",  # rounds 1 and 2, plus any extra round a DECISION grants
    r"reviews/cold/M\d+/scoped-\d+\.md",
    r"reviews/cold/M\d+/DISPOSITIONS\.md",
    r"reviews/qodo/PR-\d+/DISPOSITIONS\.md",
    r"reviews/qodo/PR-\d+/\d+/(?:issue-comment|review|review-comment)-\d+\.(?:md|json)",
))
SHA40 = re.compile(r"[0-9a-f]{40}")
COLD_SEVERITIES = ("high", "medium", "low")
TOP_COLD, TOP_QODO = "high", "action required"
BLANK = ("", "-", "—", "n/a", "none")  # cells that name nothing
DISPOSITIONS = (  # the disposition grammar shared by both tables; anything else is undecided
    ("fixed", re.compile(r"fixed in ([0-9a-fA-F]{7,40})")),
    ("dismissed", re.compile(r"dismissed:\s*(\S.*)")),
    ("deferred", re.compile(r"deferred:\s*(L-\d+) to (M\d+|phase \d+ backlog)")),
    ("pending", re.compile(r"owner decision:\s*pending \((ESCALATION-\d+)\)")),
    ("owner", re.compile(r"owner decision:\s*(\S.*?),\s*Matthew \((DECISION-\d+)\)")),
)

# Copied unchanged from qodo_review.py, the appendix of docs/QODO-REVIEW.md, so that room.py reads an
# archived Code Review comment exactly as the tool does (tests/test_gate.py checks they still match).
_HEADING = re.compile(r"<h\d>([^<]*)</h\d>")
_FINDING = re.compile(r"<summary>[ \t]*(\d+)\.[ \t]+([^\n]*?)[ \t]*</summary>")
_SEVERITY = re.compile(r'<img src="https://img\.shields\.io/badge/[^"]*"[^>]*alt="([^"]+)"')
_REVIEWED = re.compile(r"<!--\s*https://[^\s]+/commit/([0-9a-f]{40})\s*-->")
_RESOLVED_MARK = re.compile(r"✓\s*Resolved")
_CATEGORY = re.compile(r"<code>\s*([^<]*?\(\d+\))\s*</code>")
_COUNT = re.compile(r"\((\d+)\)\s*$")
_STRUCK = re.compile(r"<s>|<del>|<strike>|~~|✓\s*Resolved")


def plain(title):
    """A finding title without markup, code spans or the resolved mark: qodo_review.py's plain()
    (with its text_of()), copied from docs/QODO-REVIEW.md."""
    text = re.sub(r"<code>.*?</code>", "", title)
    text = html.unescape(re.sub(r"<[^>]+>", "", text)).replace("~~", "")
    text = _RESOLVED_MARK.sub("", text)
    return " ".join(text.replace("\\", "").split())


def title_key(title):
    """How finding titles are compared, the same way on both sides: entities unescaped, backticks dropped,
    whitespace and case folded. A table cell is compared as written: no <…> is stripped from it, since
    the tool prints titles such as "Use <path> placeholders" as plain text."""
    return " ".join(html.unescape(title).replace("`", "").split()).casefold()


SEVERITY_RANK = {"action required": 3, "remediation recommended": 2, "informational": 1}


def stricter(a, b):
    """The stricter of two Qodo severities (labels it doesn't know rank lowest)."""
    return a if SEVERITY_RANK.get((a or "").lower(), 0) >= SEVERITY_RANK.get((b or "").lower(), 0) else b


def mask_code(text):
    """TEXT with every character inside code blanked, keeping positions: <pre>…</pre>, <code>…</code> and
    fenced blocks, also when quoted with '>'. A severity badge quoted from the PR's code in a finding's
    excerpt is not Qodo's. qodo_review.py has the same weakness (it reads every badge), so the severity
    the tool prints after such a quote can be wrong; the gate reads the severity itself."""
    def blank(s):
        return re.sub(r"[^\n]", " ", s)

    out, fenced = [], False
    for line in text.splitlines(keepends=True):
        fence = re.match(r"[> \t]*(```|~~~)", line)
        out.append(blank(line) if fenced or fence else line)
        if fence:
            fenced = not fenced
    return re.sub(r"<pre>.*?</pre>|<code>.*?</code>", lambda m: blank(m.group(0)), "".join(out), flags=re.S)


def header_total(text):
    """qodo_review.py's header_total(): the open findings the header counts, or None without counts."""
    counts = [int(m.group(1)) for label in _CATEGORY.findall(text.split("<details", 1)[0])
              for m in [_COUNT.search(label.strip())] if m]
    return sum(counts) if counts else None


def is_code_review(text):
    """qodo_review.py's is_code_review(): the comment's first heading names the Code Review."""
    m = _HEADING.search(text)
    return "Code Review" in (m.group(1) if m else (text.strip().splitlines() or [""])[0])


def qodo_findings(text):
    """[{number, title, key, severity}] of a Code Review comment, severity from the last badge above
    each finding, not counting badges inside code."""
    badges = [(m.start(), m.group(1)) for m in _SEVERITY.finditer(mask_code(text))]
    out = []
    for m in _FINDING.finditer(text):
        severity = None
        for position, label in badges:
            if position < m.start():
                severity = label
        title = plain(m.group(2).strip())
        out.append({"number": m.group(1), "title": title, "key": title_key(title), "severity": severity,
                    "resolved": bool(_STRUCK.search(m.group(2)))})
    return out


def qodo_titles(fetches):
    """{title key: {title, severity, first}} over every archived fetch: the strictest severity any finding
    of that title had, and the reviewed commit of the first fetch that shows it open (None when no fetch
    does: then a fix has no lower bound but the PR's own commits)."""
    out = {}
    for f in fetches:
        for x in f["findings"]:
            t = out.setdefault(x["key"], {"title": x["title"], "severity": x["severity"], "first": None})
            t["severity"] = stricter(x["severity"], t["severity"])
            if not x["resolved"] and t["first"] is None:
                t["first"] = f["reviewed"]
    return out


def exempt(path):
    """A review record that the coverage rule exempts: the whole path matches one of REVIEW_EXEMPT."""
    return any(p.fullmatch(path) for p in REVIEW_EXEMPT)


def parse_disposition(cell):
    """(form, match) for a disposition cell, or (None, None) when it is undecided."""
    text = " ".join(cell.replace("`", "").split())
    for form, rx in DISPOSITIONS:
        m = rx.fullmatch(text)
        if m:
            return form, m
    return None, None


def md_cells(line):
    """The cells of a markdown table row, or None for a line that isn't one."""
    s = line.strip()
    if not s.startswith("|"):
        return None
    s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def md_tables(text):
    """[(lowercased header cells, [row cells])] of every markdown table in text. Blank lines inside a
    table don't end it (so no row after one is lost); after blank lines, a table line starts a new
    table only when a separator row follows it."""
    def separator(cells):
        return cells is not None and all(re.fullmatch(r":?-+:?", c) for c in cells)

    lines = text.splitlines()
    out, rows, sep, gap = [], None, False, False
    for i, line in enumerate(lines):
        if not line.strip():
            gap = rows is not None
            continue
        cells = md_cells(line)
        if cells is None:
            rows, gap = None, False
            continue
        header_next = not separator(cells) and separator(md_cells(lines[i + 1]) if i + 1 < len(lines) else None)
        if rows is None or (gap and header_next):
            rows, sep = [], False
            out.append(([c.lower() for c in cells], rows))
        elif not sep and not rows and separator(cells):
            sep = True
        else:
            rows.append(cells)
        gap = False
    return out


def find_table(text, required, optional=()):
    """Rows, as {column: cell}, of the first table whose header has every REQUIRED column; None if none.
    A column is named by its header cell or a prefix of it ('finding' for 'finding (title as…)')."""
    for header, rows in md_tables(text or ""):
        idx = {}
        for col in (*required, *optional):
            i = next((j for j, h in enumerate(header) if h == col), None)
            i = next((j for j, h in enumerate(header) if h.startswith(col)), None) if i is None else i
            if i is not None:
                idx[col] = i
        if all(c in idx for c in required):
            return [{c: (r[i] if i < len(r) else "") for c, i in idx.items()} for r in rows]
    return None


def machine_lines(text):
    """The `key: value` lines that open a record, up to its first table or ## heading."""
    values = {}
    for line in text.splitlines():
        if line.startswith("## ") or line.lstrip().startswith("|"):
            break
        key, sep, value = line.partition(":")
        if sep and re.fullmatch(r"[a-z][a-z -]*", key.strip()):
            values[key.strip()] = re.sub(r"\s+#.*$", "", value).strip()
    return values


def ledger_entries(text):
    """{L-n: {id, source, finding, target, status}} from LEDGER.md's table, the first row of each ID."""
    out = {}
    for row in find_table(text or "", ("id", "source", "target", "status"), ("finding",)) or []:
        lid = row["id"].strip("` ")
        if re.fullmatch(r"L-\d+", lid):
            out.setdefault(lid, row)
    return out


def folded(text):
    return " ".join(text.replace("`", "").split()).lower()


def ledger_problems(entry, finding, target):
    """Why ledger ENTRY doesn't record this deferral: [] when its status is open, its target is TARGET
    and its source names FINDING: ("cold", M<k>, ID) or ("qodo", PR number, title)."""
    out = []
    if folded(entry["status"]) != "open":
        out.append(f"its status is '{entry['status']}', not open")
    if folded(entry["target"]) != folded(target):
        out.append(f"its target is '{entry['target']}', not {target}")
    kind, where, what = finding
    source = entry["source"]
    if kind == "cold":
        named = all(re.search(rf"(?<![\w-]){re.escape(x)}(?![\w-])", source) for x in (where, what))
        expected = f"cold {where} {what}"
    else:
        named = bool(re.search(rf"PR #{where}(?!\d)", source)) and \
            any(title_key(what) in title_key(cell) for cell in (source, entry.get("finding", "")))
        expected = f"qodo PR #{where} and the title"
    if not named:
        out.append(f"its source '{source}' doesn't name {expected}")
    return out


def glob_regex(glob):
    """A merge-hold glob as a regex on the whole path, ignoring case: '*' within a segment, '**' across
    segments, and '**/' any number of whole directories, none included (`**/go.mod` matches go.mod and
    lib/go.mod). Case is ignored so that AuthContext.tsx is held like auth.py."""
    out, i = [], 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("".join(out), re.IGNORECASE)


def merge_hold_rules(playbook):
    """[(label, glob, deleted_only, regex)] from the "## Merge-hold list" section of PLAYBOOK.md, one
    bullet per area (- <label>: `glob`, `glob`), whose globs may go on over indented continuation lines.
    None when the section is missing. A label containing "deleted" matches only deleted paths."""
    m = re.search(r"^##[ \t]+Merge-hold list[^\n]*\n(.*?)(?=^##[ \t]|\Z)", playbook or "", re.M | re.S | re.I)
    if not m:
        return None
    rules, label = [], None
    for line in m.group(1).splitlines():
        b = re.match(r"\s*[-*+][ \t]+(.*)", line)
        if b:
            label = b.group(1).split("`", 1)[0].strip().rstrip(":").strip()
            text = b.group(1)
        elif label is not None and re.match(r"[ \t]+\S", line):
            text = line  # an indented continuation line of the same bullet
        else:
            if line.strip():
                label = None  # unindented text ends the bullet; a blank line doesn't
            continue
        for glob in re.findall(r"`([^`]+)`", text):
            rules.append((label, glob.strip(), "deleted" in label.lower(), glob_regex(glob.strip())))
    return rules


# --- reading the mission branch

def project_root():
    """The top of the project checkout the gate runs in; an error when this isn't a checkout of REPO."""
    here = repo_from_checkout()
    r = git("rev-parse", "--show-toplevel", check=False)
    if not here or here.lower() != REPO.lower() or r.returncode != 0:
        raise StateError(f"run this inside a checkout of {REPO}")
    return r.stdout.strip()


def blob(root, rev, path):
    r = git("show", f"{rev}:{path}", cwd=root, check=False)
    return r.stdout if r.returncode == 0 else None


def zsplit(out):
    return [p for p in out.split("\0") if p]


def resolve_commit(root, rev):
    r = git("rev-parse", "--verify", "-q", f"{rev}^{{commit}}", cwd=root, check=False)
    return r.stdout.strip() if r.returncode == 0 else None


def commit_files(root, sha):
    """The paths a commit changed against its first parent (every path, for a root commit), so that a
    lead's merge of a builder branch touches what the merge brought in, not what the other side did."""
    parents = git_out("rev-list", "--parents", "-n", "1", sha, cwd=root).split()[1:]
    if parents:
        return set(zsplit(git("diff", "--name-only", "--no-renames", "-z", parents[0], sha, cwd=root).stdout))
    return set(zsplit(git("diff-tree", "--no-commit-id", "--name-only", "-r", "--root", "-z", sha, cwd=root).stdout))


def parse_cold_report(path, kind, number, text):
    """A cold report: the commit it covers, its findings {ID: severity} and what's wrong with it."""
    covers = machine_lines(text).get("covers", "").lower()
    prefix = ("R" if kind == "round" else "S") + str(number)
    rows = find_table(text, ("id", "severity"))
    findings, errors = {}, []
    if rows is None:
        errors.append(f"{path} has no findings table (| ID | severity | …)")
    for row in rows or []:
        fid = row["id"].strip("` ")
        if fid.lower() in BLANK:
            continue
        sev = row["severity"].strip("` ").lower()
        if not re.fullmatch(rf"{prefix}-\d+", fid):
            errors.append(f"{path}: finding ID {fid} is not {prefix}-<n>")
        if sev not in COLD_SEVERITIES:
            errors.append(f"{path}: {fid} has severity '{row['severity']}', not high, medium or low")
        if fid in findings:
            errors.append(f"{path}: {fid} appears twice")
        findings[fid] = sev
    return {"path": path, "covers": covers if SHA40.fullmatch(covers) else None, "findings": findings,
            "errors": errors}


def review_records(root, sha, mission, pr):
    """The mission's cold records and the PR's Qodo records, as committed at sha."""
    paths = zsplit(git("ls-tree", "-r", "--name-only", "-z", sha, "--", "reviews", cwd=root).stdout)
    cold, fetches, dirs = [], {}, set()
    for p in sorted(paths):
        m = re.fullmatch(rf"reviews/cold/{re.escape(mission)}/(round|scoped)-(\d+)\.md", p)
        if m:
            cold.append(parse_cold_report(p, m.group(1), int(m.group(2)), blob(root, sha, p) or ""))
        m = re.fullmatch(rf"reviews/qodo/PR-{pr}/(\d+)/.+", p)
        if m:
            dirs.add(int(m.group(1)))  # every archived fetch directory, with a Code Review comment or not
        m = re.fullmatch(rf"reviews/qodo/PR-{pr}/(\d+)/issue-comment-(\d+)\.md", p)
        if m:
            fetches.setdefault(int(m.group(1)), []).append((int(m.group(2)), p))
    archived = []  # every fetch holding a Code Review comment (its newest, if several), oldest first
    for k in sorted(fetches):
        reviews = [(cid, p, text) for cid, p in fetches[k]
                   for text in [blob(root, sha, p) or ""] if is_code_review(text)]
        if reviews:
            _, p, text = max(reviews)
            hits = _REVIEWED.findall(text)
            archived.append({"fetch": k, "path": p, "reviewed": hits[-1] if hits else None,
                             "findings": qodo_findings(text), "header": header_total(text)})
    qodo_text = blob(root, sha, f"reviews/qodo/PR-{pr}/DISPOSITIONS.md")
    return {"mission": mission, "pr": pr, "cold": cold, "qodo": archived[-1] if archived else None,
            "qodo_fetches": archived, "qodo_dirs": sorted(dirs),
            "cold_path": f"reviews/cold/{mission}/DISPOSITIONS.md",
            "cold_dispositions": blob(root, sha, f"reviews/cold/{mission}/DISPOSITIONS.md"),
            "qodo_path": f"reviews/qodo/PR-{pr}/DISPOSITIONS.md",
            "qodo_dispositions": qodo_text,
            "qodo_mode": machine_lines(qodo_text).get("qodo") if qodo_text is not None else None}


class Gate:
    """The gate's check lines, and the verdict they add up to."""

    def __init__(self):
        self.holds, self.fixes, self.waits = set(), [], []

    def ok(self, name, text):
        print(f"✓ {name}: {text}", flush=True)

    def wait(self, name, text):
        print(f"… {name}: {text}", flush=True)
        self.waits.append(f"{name}: {text}")

    def fail(self, name, reasons):
        """reasons: [(text, hold reason or None)]. None: the lead fixes it; it is no reason to hold."""
        print(f"✗ {name}: {'; '.join(t for t, _ in reasons)}", flush=True)
        self.holds |= {h for _, h in reasons if h}
        if any(h is None for _, h in reasons):
            self.fixes.append(name)

    def verdict(self, head):
        if self.holds or self.fixes:
            line = "gate: FAIL hold reasons " + (", ".join(str(h) for h in sorted(self.holds)) or "none")
            line += f"; fix first: {', '.join(self.fixes)}" if self.fixes else ""
            print(line + (f" (head {head[:12]})" if head else ""))  # the head a hold names (M6f)
            return EXIT_FAIL
        if self.waits:
            print("gate: WAIT " + "; ".join(self.waits))
            return EXIT_WAIT
        print(f"gate: PASS {head}")
        return 0


# --- the checks

def check_coverage(g, root, head, rec):
    covered, errors = [], []
    for r in rec["cold"]:
        if r["covers"]:
            covered.append((r["covers"], r["path"]))
        else:
            errors.append(f"{r['path']}: 'covers:' must name the reviewed commit's 40-hex sha")
    q = rec["qodo"]  # Qodo's review covers code only when its findings are decided: qodo: on
    if q and rec["qodo_mode"] == "on" and q["reviewed"]:
        covered.append((q["reviewed"], f"Qodo fetch {q['fetch']}"))
    elif q and rec["qodo_mode"] == "on":
        errors.append(f"{q['path']}: no reviewed-commit marker in the Code Review comment")
    best = None  # (commit, source, uncovered paths, commits since) of the review closest to covering HEAD
    for commit, source in covered:
        if is_ancestor(root, commit, head):
            changed = zsplit(git("diff", "--name-only", "--no-renames", "-z", commit, head, cwd=root).stdout)
            uncovered = [p for p in changed if not exempt(p)]
            since = int(git_out("rev-list", "--count", f"{commit}..{head}", cwd=root))
            if best is None or (len(uncovered), since) < (len(best[2]), best[3]):
                best = (commit, source, uncovered, since)
    if not covered:
        errors.append("no recorded review: no cold report of this mission and no archived Qodo review of this PR")
    elif best is None:
        errors.append("no recorded review covers a commit of this branch: " +
                      ", ".join(f"{s} covers {c[:12]}" for c, s in covered))
    elif best[2]:
        errors.append(f"changed since the closest review ({best[1]}, {best[0][:12]}): {', '.join(best[2])}; "
                      "a scoped cold review must cover them")
    if errors:
        g.fail("coverage", [(e, None) for e in errors])
    else:
        note = "it is HEAD" if best[0] == head else "only review records changed since"
        g.ok("coverage", f"{best[1]} covers {best[0][:12]}; {note}")


def row_files(cell):
    """The paths named in a table's file cell, line numbers dropped."""
    out = []
    for item in re.split(r"[,\s]+", cell.replace("`", "")):
        item = re.sub(r":\d+(?:-\d+)?$", "", item.strip())
        if item.lower() not in BLANK:
            out.append(item)
    return out


def same_commit(line, sha):
    """Whether a record's commit LINE names SHA: backticks stripped, a hex prefix of 7 or more characters,
    any text after it ignored (`95eebe4…` (fetch 3))."""
    m = re.match(r"([0-9a-f]{7,40})(?![0-9a-z])", line.replace("`", "").strip().lower())
    return bool(m and sha and sha.startswith(m.group(1)))


def target_problem(target, mission, phase):
    """Why a deferral TARGET isn't later than MISSION (M<k>) or the current PHASE, or None."""
    m = re.fullmatch(r"M(\d+)", target)
    if m:
        return None if int(m.group(1)) > int(mission[1:]) else f"which is not a mission after {mission}"
    p = int(re.fullmatch(r"phase (\d+) backlog", target).group(1))
    if phase is None:
        return "but MISSIONS.md records no current phase to compare with"
    return None if p > phase else f"which is not a phase after the current phase {phase}"


def judge(root, head, label, cell, top, file_cell, ledger, reported=None, room=None, finding=None, mission=None,
          phase=None):
    """What is wrong with one dispositions row: [(text, hold reason or None)]. REPORTED is the commit the
    finding was reported against: a cold report's covers:, or the first Qodo fetch showing the title open.
    ROOM (a RoomLog) answers whether an owner decision on a top-severity row is really Matthew's. LEDGER is
    ledger_entries(); FINDING names the finding for a deferral's ledger row (see ledger_problems). A deferral
    targets a mission after MISSION or a phase after PHASE."""
    form, m = parse_disposition(cell)
    if form is None:
        return [(f"{label} is undecided" + (f" ('{cell}')" if cell.strip() else ""), 2)]
    if form == "pending":
        return [(f"{label} waits on an open owner decision ({m.group(1)})", 1)]
    if top and form in ("dismissed", "deferred"):
        return [(f"{label} is top severity, so only a fix or an owner decision closes it, not '{form}'", 1)]
    owner_check = top and form == "owner" and room is not None and finding
    answer, edited = room.answers(m.group(2), finding) if owner_check else (None, False)
    if owner_check and not answer:
        n, what = m.group(2).rsplit("-", 1)[1], finding[2]
        if edited:
            return [(f"{label} cites {m.group(2)}, but the lead's ESCALATION-{n} or MERGE-HOLD-{n} about {what} was "
                     f"edited after {m.group(2)}: post a new escalation or hold", 1)]
        return [(f"{label} cites {m.group(2)}, but {room.where()} has no trusted {m.group(2)} answering the lead's "
                 f"earlier ESCALATION-{n} or MERGE-HOLD-{n} about {what}", 1)]
    if form == "deferred" and mission:
        late = target_problem(m.group(2), mission, phase)
        if late:
            return [(f"{label}: deferred to {m.group(2)}, {late}", None)]
    if form == "deferred" and m.group(1) not in ledger:
        return [(f"{label}: {m.group(1)} is not in {PLAYBOOK_DIR}/LEDGER.md on {STATE_BRANCH}", None)]
    if form == "deferred" and finding:
        lacking = ledger_problems(ledger[m.group(1)], finding, m.group(2))
        if lacking:
            return [(f"{label}: ledger {m.group(1)} doesn't record this deferral: {', '.join(lacking)}", None)]
    if form == "fixed":
        short = m.group(1).lower()
        full = resolve_commit(root, short)
        if not full:
            return [(f"{label}: fixed in {short}: no such commit", None)]
        if not is_ancestor(root, full, head):
            return [(f"{label}: fixed in {short}, which is not an ancestor of HEAD", None)]
        if is_ancestor(root, full, "refs/remotes/origin/main"):
            return [(f"{label}: fixed in {short}, which is already on main", None)]
        if reported and is_ancestor(root, full, reported):
            return [(f"{label}: fixed in {short}, which the review that found it had already seen "
                     f"({reported[:12]})", None)]
        files = row_files(file_cell)
        touched = commit_files(root, full) if files else set()
        if files and not any(f in touched or (f.endswith("/") and any(t.startswith(f) for t in touched))
                             for f in files):
            return [(f"{label}: fixed in {short}, which doesn't touch {', '.join(files)}", None)]
    return []


def check_dispositions(g, root, head, rec, ledger_text, room, phase=None):
    reasons, ledger = [], ledger_entries(ledger_text)
    # cold: a row for every finding ID of every report
    want, reported = {}, {}
    for r in rec["cold"]:
        reasons += [(e, None) for e in r["errors"]]
        want.update(r["findings"])
        reported.update({fid: r["covers"] for fid in r["findings"]})
    n_cold = n_qodo = 0
    if rec["cold_dispositions"] is None:
        reasons.append((f"{rec['cold_path']} is missing", None))
    else:
        rows = find_table(rec["cold_dispositions"], ("id", "disposition"), ("severity", "file"))
        if rows is None:
            reasons.append((f"{rec['cold_path']} has no | ID | … | disposition | table", None))
        seen = set()
        for row in rows or []:
            fid = row["id"].strip("` ")
            if fid.lower() in BLANK:
                continue
            if fid in seen:
                reasons.append((f"{rec['cold_path']}: {fid} has two rows", None))
            seen.add(fid)
            n_cold += 1
            top = TOP_COLD in (want.get(fid), row.get("severity", "").strip("` ").lower())
            reasons += judge(root, head, f"cold {fid}", row["disposition"], top, row.get("file", ""), ledger,
                             reported.get(fid), room, ("cold", rec["mission"], fid), rec["mission"], phase)
        missing = [fid for fid in want if fid not in seen]
        if rows is not None and missing:
            reasons.append((f"{rec['cold_path']} has no row for {', '.join(missing)}", None))
    # Qodo: with QODO_REVIEW=on the file exists; with qodo: on, a row for every finding of the latest archive
    switch = os.environ.get("QODO_REVIEW", "").strip()
    if switch not in ("on", "off"):
        reasons.append((f"QODO_REVIEW must be on or off, not {switch!r}", None))
    text, path, q = rec["qodo_dispositions"], rec["qodo_path"], rec["qodo"]
    if rec["qodo_fetches"] and rec["qodo_mode"] != "on":  # an archived review is never ignored
        fetched = ", ".join(str(f["fetch"]) for f in rec["qodo_fetches"])
        reasons.append((f"Qodo's review of this PR is archived (fetches {fetched}), so {path} must exist and "
                        f"say qodo: on" + (f", not {rec['qodo_mode']}" if rec["qodo_mode"] else ""), None))
    elif text is None and switch == "on":
        reasons.append((f"{path} is missing (QODO_REVIEW=on)", None))
    if text is not None:
        lines = machine_lines(text)
        mode = lines.get("qodo")
        if mode not in ("on", "off", "no first review"):
            reasons.append((f"{path}: its 'qodo:' line must be on, off or no first review", None))
        rows = find_table(text, ("#", "finding", "disposition"), ("severity", "file"))
        if rows is None and mode == "on":
            reasons.append((f"{path} has no | # | … | finding | … | disposition | table", None))
        titles = qodo_titles(rec["qodo_fetches"])  # every finding of every fetch, absent now or not
        seen = set()
        for row in rows or []:
            key = title_key(row["finding"])
            if not key and not row["disposition"].strip():
                continue
            if key in seen:  # exactly one disposition per finding
                reasons.append((f"{path}: two rows for: {' '.join(row['finding'].split())}", None))
            seen.add(key)
            n_qodo += 1
            t = titles.get(key) or {}
            top = TOP_QODO in ((t.get("severity") or "").lower(), row.get("severity", "").strip("` ").lower())
            label = f"Qodo #{row['#'].strip() or '?'} \"{' '.join(row['finding'].split())}\""
            reasons += judge(root, head, label, row["disposition"], top, row.get("file", ""), ledger, t.get("first"),
                             room, ("qodo", rec["pr"], t.get("title") or " ".join(row["finding"].split())),
                             rec["mission"], phase)
        if mode == "on" and q is None:
            reasons.append((f"{path} says qodo: on, but no Code Review comment is archived for this PR", None))
        elif mode == "on":
            missing = [t["title"] for key, t in titles.items() if key not in seen]
            if missing:
                fetched = ", ".join(str(f["fetch"]) for f in rec["qodo_fetches"])
                reasons.append((f"{path} has no row for: {'; '.join(missing)} (archived fetches {fetched})", None))
            # the archive is whole: fetches 1..k as the tool numbers them, as the table says it was built from
            dirs = rec["qodo_dirs"]
            if dirs != list(range(1, len(dirs) + 1)):
                reasons.append((f"reviews/qodo/PR-{rec['pr']}/ holds fetches {', '.join(map(str, dirs))}, not 1 to "
                                f"{len(dirs)}: restore the missing fetch", None))
            listed = [int(x) for x in re.findall(r"\d+", lines.get("fetches", ""))]
            if listed != dirs:
                reasons.append((f"{path} says fetches: {lines.get('fetches') or '(none)'}, but the archived fetches "
                                f"are {', '.join(map(str, dirs))}", None))
            if not same_commit(lines.get("reviewed", ""), q["reviewed"]):
                reasons.append((f"{path} says reviewed: {lines.get('reviewed') or '(none)'}, but the last fetch "
                                f"reviewed {q['reviewed'] or '(no marker)'}", None))
    # QODO-REVIEW rule 5: the header's open count must agree with the open findings that parse; and every
    # finding has a severity. Either failure means Qodo's format moved: the fix is a patch to room.py's
    # parser, not a change to the records
    patch = "the records can't fix this: room.py's Qodo parser needs a patch"
    for f in rec["qodo_fetches"]:
        open_ = sum(1 for x in f["findings"] if not x["resolved"])
        if f["header"] is None or f["header"] != open_:
            counted = "no header counts" if f["header"] is None else f"the header counts {f['header']} open"
            reasons.append((f"Qodo comment did not parse: read it ({f['path']}: {counted}, {open_} parsed open; "
                            f"{patch})", None))
        unrated = [f"#{x['number']} \"{x['title']}\"" for x in f["findings"]
                   if (x["severity"] or "").lower() not in SEVERITY_RANK]
        if unrated:
            reasons.append((f"severity did not parse: read the comment ({f['path']}: {', '.join(unrated)}; {patch})",
                            None))
    if reasons:
        g.fail("dispositions", reasons)
    else:
        g.ok("dispositions", f"{n_cold} cold and {n_qodo} Qodo row(s), every finding decided")


def required_contexts():
    """({(context, app id or None)} required on main, or None, error text). A check that names its app
    (app_id in classic protection, integration_id in rulesets; -1 or none: any app) is satisfied only by
    a check run from that app; a name required without one by any run or status of that name."""
    req = set()

    def add(context, app):
        if context:
            req.add((context, app if isinstance(app, int) and app >= 0 else None))

    status, prot = gh_try(f"repos/{REPO}/branches/main/protection")
    if status == 200 and isinstance(prot, dict):
        rsc = prot.get("required_status_checks") or {}
        for context in rsc.get("contexts") or []:
            add(context, None)
        for c in rsc.get("checks") or []:
            add(c.get("context"), c.get("app_id"))
    elif not unprotected(status, prot):
        return None, f"can't read main's protection: {prot}"
    status, rules = gh_try(f"repos/{REPO}/rules/branches/main")
    if status == 200 and isinstance(rules, list):
        for rule in rules:
            if rule.get("type") == "required_status_checks":
                for c in (rule.get("parameters") or {}).get("required_status_checks") or []:
                    add(c.get("context"), c.get("integration_id"))
    elif status != 200 and not unprotected(status, rules):
        return None, f"can't read main's rules: {rules}"
    # classic protection lists every check under contexts too: a name bound to an app keeps only that binding
    bound = {c for c, app in req if app is not None}
    return {(c, app) for c, app in req if app is not None or c not in bound}, None


def gh_pages(path, key):
    out, page = [], 1
    while True:
        batch = (gh(f"{path}{'&' if '?' in path else '?'}per_page=100&page={page}") or {}).get(key) or []
        out += batch
        if len(batch) < 100:
            return out
        page += 1


CHECKS_GRACE = 600  # seconds a new HEAD with workflows may have no runs before "no checks ran" passes
LATE_LIMIT = 3600  # seconds a required context may stay unreported while other checks are pending
WORKFLOW = glob_regex(".github/workflows/*.y*ml")


def check_checks(g, root, head, pr_updated=None):
    required, err = required_contexts()
    if err:
        g.fail("checks", [(err, None)])
        return
    rank = {"ok": 0, "pending": 1, "failed": 2}
    # filter=latest already drops superseded re-runs; two workflows may each have a job of the same
    # name, so runs are told apart by check suite as well as by name
    runs = {}
    for run in gh_pages(f"repos/{REPO}/commits/{head}/check-runs?filter=latest", "check_runs"):
        key = ((run.get("check_suite") or {}).get("id"), run.get("name"))
        if run.get("name") and run.get("id", 0) >= runs.get(key, {}).get("id", 0):
            runs[key] = run
    results = [(name, "pending" if run.get("status") != "completed" else
                "ok" if run.get("conclusion") in ("success", "neutral", "skipped") else "failed",
                (run.get("app") or {}).get("id"))
               for (_, name), run in runs.items()]
    statuses = {}
    for s in gh_pages(f"repos/{REPO}/commits/{head}/status", "statuses"):
        if s.get("context"):  # a context reported twice counts at its worst
            v = {"success": "ok", "pending": "pending"}.get(s.get("state"), "failed")
            statuses[s["context"]] = max(statuses.get(s["context"], v), v, key=rank.get)
    results += [(context, v, None) for context, v in statuses.items()]  # a status names no app
    failed = sorted({c for c, v, _ in results if v == "failed"})
    missing = sorted(context + (f" (from app {app})" if app is not None else "") for context, app in required
                     if not any(c == context and (app is None or a == app) for c, _, a in results))
    pending = sorted({c for c, v, _ in results if v == "pending"})
    if failed:
        g.fail("checks", [(t, 3) for t in (f"failed: {', '.join(failed)}",
                                            f"required but missing: {', '.join(missing)}" if missing else None) if t])
        return
    # with workflows in HEAD, Actions may not have created its runs yet; other apps' results don't tell.
    # Wait from the later of HEAD's commit and the PR's last update (a push of an older commit moves the PR)
    workflows = [p for p in zsplit(git("ls-tree", "-r", "--name-only", "-z", head, "--", ".github/workflows",
                                       cwd=root).stdout) if WORKFLOW.fullmatch(p)]
    no_actions = bool(workflows) and not any((r.get("app") or {}).get("slug") == "github-actions"
                                             for r in runs.values())
    changed = int(git_out("log", "-1", "--format=%ct", head, cwd=root))
    try:
        changed = max(changed, calendar.timegm(time.strptime(pr_updated or "", "%Y-%m-%dT%H:%M:%SZ")))
    except ValueError:
        pass
    age = int(time.time()) - changed  # since the later of HEAD's commit and the PR's last update
    if no_actions:
        if age < CHECKS_GRACE:
            g.wait("checks", f"no GitHub Actions runs for HEAD yet, though it has {len(workflows)} workflow(s); "
                             f"last change {max(age, 0)}s ago (waiting up to {CHECKS_GRACE // 60} minutes)")
            return
    if pending and missing and age >= LATE_LIMIT:  # late for an hour: it isn't coming
        g.fail("checks", [(f"required but missing: {', '.join(missing)}, still not reported {LATE_LIMIT // 60} minutes "
                           f"after the last change (pending: {', '.join(pending)})", 3)])
    elif pending:  # a required context that hasn't reported may be late while others still run
        g.wait("checks", f"pending: {', '.join(pending)}" + (f"; not reported yet: {', '.join(missing)}" if missing else ""))
    elif missing:
        g.fail("checks", [(f"required but missing: {', '.join(missing)}", 3)])
    elif not results:
        g.ok("checks", "no checks ran for HEAD" if workflows else "no checks configured")
    else:
        g.ok("checks", f"{len(results)} passed" + (f" (required: {', '.join(sorted({c for c, _ in required}))})" if required else "")
             + ("; no GitHub Actions runs for HEAD" if no_actions else ""))


def current_room(playbook, values):
    """(number, where) of the current room: PLAYBOOK.md's `room:` line, where the architect records it at each
    phase's kickoff, else the machine block VALUES' room; None if neither names one. The gate and the watchdog
    both use it."""
    m = re.search(r"^room:[ \t]*(\d+)", playbook or "", re.M)
    for n, where in ((m.group(1) if m else None, "PLAYBOOK.md"), ((values or {}).get("room"), "MISSIONS.md")):
        if (n or "").strip().isdigit() and int(n) > 0:
            return int(n), where
    return None


def room_number(playbook, missions):
    """The current room's number (see current_room), with MISSIONS.md as text; None if no room is recorded."""
    try:
        values = read_block(missions or "")
    except StateError:
        values = {}
    found = current_room(playbook, values)
    return found[0] if found else None


class RoomLog:
    """The room's trusted messages, read once, and only when a check needs them."""

    def __init__(self, playbook, missions):
        self.number = room_number(playbook, missions)
        self._messages = None

    def where(self):
        return f"room {self.number}" if self.number else "the room (none is recorded in PLAYBOOK.md or MISSIONS.md)"

    def messages(self):
        """Trusted messages, each with "edited": its updated_at (an edit keeps the comment's id)."""
        if self._messages is None:
            self._messages = [dict(m, edited=c.get("updated_at") or m["at"])
                              for c in (comments(self.number) if self.number else [])
                              for m in [parse(c)] if trusted(m)]
        return self._messages

    def decisions(self, kind):
        """The trusted messages of KIND (DECISION-n) from the architect, or untagged from Matthew, oldest first."""
        return [m for m in self.messages() if m["role"] in ("architect", "human") and message_kind(m["text"]) == kind]

    @staticmethod
    def before(ask, decision):
        """Whether ASK (a hold or escalation) stood as it is now when DECISION was posted: posted before it
        and not edited since."""
        return ask["id"] < decision["id"] and ask["edited"] <= decision["at"]

    def answers(self, decision, finding):
        """(the trusted DECISION-n that answers the lead's earlier ESCALATION-n or MERGE-HOLD-n naming FINDING,
        or None; whether such a message exists but was edited after the decision). FINDING is ("cold", M<k>,
        ID) or ("qodo", PR, title). A message names it by its cold ID, by the full Qodo title, or by the
        dispositions file the finding sits in, as v1's "point to files instead of pasting" asks."""
        n = decision.rsplit("-", 1)[1]
        kind, where, what = finding
        record = f"reviews/cold/{where}/DISPOSITIONS.md" if kind == "cold" else f"reviews/qodo/PR-{where}/DISPOSITIONS.md"

        def names(text):
            if record in message_tokens(text):
                return True
            if kind == "cold":
                return re.search(rf"(?<![\w-]){re.escape(what)}(?![\w-])", text)
            return re.search(rf"(?<!\w){re.escape(title_key(what))}(?!\w)", title_key(text))

        asks = [m for m in self.messages() if m["role"] == "lead" and names(m["text"])
                and message_kind(m["text"]) in (f"ESCALATION-{n}", f"MERGE-HOLD-{n}")]
        decisions = self.decisions(decision)
        answer = next((d for d in decisions if any(self.before(e, d) for e in asks)), None)
        edited = answer is None and any(e["id"] < d["id"] for e in asks for d in decisions)
        return answer, edited

    def holds(self, kind):
        """The lead's trusted messages of KIND (MERGE-HOLD-n)."""
        return [m for m in self.messages() if m["role"] == "lead" and message_kind(m["text"]) == kind]

    def later_hold(self, pr, after):
        """The lead's newest trusted MERGE-HOLD, of any number, after comment AFTER that supersedes a reason-5 hold
        for PR #pr, or None: its first line names PR #pr, and not only reasons other than 5. A hold for another
        reason only (3, 4 or 6, say after a 405) doesn't supersede (cold M6f scoped-1 S1-1); one whose first line
        names no reason number, or `reasons 1 and 5`, does: in doubt it supersedes (cold M6f scoped-2 S2-1)."""
        def supersedes(m):
            reasons = hold_reasons(m["text"])
            return re.search(rf"PR #{pr}(?!\d)", m["text"].split("\n", 1)[0]) and (not reasons or 5 in reasons)
        holds = [m for m in self.messages() if m["id"] > after and m["role"] == "lead"
                 and base_kind(message_kind(m["text"])) == "MERGE-HOLD" and supersedes(m)]
        return max(holds, key=lambda m: m["id"], default=None)


def message_tokens(text):
    """The whole tokens of a room message, for naming paths: backticked text, and the words split on
    whitespace and commas with quotes, trailing '.', ',', ';', ':' and unbalanced parentheses dropped, so
    that src/app/(auth)/page.tsx and "(see app/auth.py)." both name their path."""
    out = set(re.findall(r"`([^`]+)`", text))
    for tok in re.split(r"[\s,]+", text):
        while True:
            before = tok
            tok = tok.strip("\"'`").rstrip(".,;:")
            if tok.endswith(")") and tok.count(")") > tok.count("("):
                tok = tok[:-1]
            if tok.startswith("(") and tok.count("(") > tok.count(")"):
                tok = tok[1:]
            if tok == before:
                break
        out.add(tok)
        if tok.startswith("(") and tok.endswith(")"):
            out.add(tok[1:-1])
    return out


HOLD_HEAD = re.compile(r"(?:,\s*|\s)head\s+([0-9a-f]{12,40})\.?\s*$", re.I)
HOLD_REASONS = re.compile(r"\breasons?\s+(\d(?:\d|\s|,|/|&|and|or)*)", re.I)


def hold_reasons(text):
    """The reason numbers a MERGE-HOLD's first line attaches to `reason` or `reasons` (reason 3, reason 3, reason 6,
    reasons 1 and 5, reasons 3, 6), as a set: empty when it names none."""
    first = (text or "").split("\n", 1)[0]
    return {int(d) for group in HOLD_REASONS.findall(first) for d in re.findall(r"\d+", group)}


def hold_head(text):
    """The head a MERGE-HOLD was posted for: the `head <hex>` (12 to 40 hex digits, after a comma or a space) that
    ends its first line, with one period after it at most (cold M6f scoped-1 S1-2), lowercased, or None. Heads it
    mentions anywhere else, an older hold's or a quoted refusal's, don't count (cold M6f R1-1)."""
    m = HOLD_HEAD.search((text or "").split("\n", 1)[0])
    return m.group(1).lower() if m else None


def commit_by_prefix(root, hexid):
    """The one commit whose id starts with HEXID, or None. Only object ids count (rev-parse --disambiguate), so
    a branch or tag named like HEXID can't stand in for it (cold M6f R1-3)."""
    ids = git("rev-parse", f"--disambiguate={hexid}", cwd=root, check=False).stdout.split()
    commits = [i for i in ids if git("cat-file", "-t", i, cwd=root, check=False).stdout.strip() == "commit"]
    return commits[0] if len(commits) == 1 else None


def hold_problems(text, pr, paths):
    """What a MERGE-HOLD message lacks for a reason-5 hold of PR's PATHS: [] when it names them all, each
    as a whole token (message_tokens), and the head it was posted for."""
    out = [] if re.search(rf"PR #{pr}(?!\d)", text) else [f"PR #{pr}"]
    out += [] if re.search(r"\breason 5\b", text, re.I) else ["reason 5"]
    tokens = message_tokens(text)
    out += [p for p in paths if p not in tokens]
    return out + ([] if hold_head(text) else ["a head"])


def hold_head_problem(root, text, n, pr, head):
    """Why MERGE-HOLD-N (TEXT, whole by hold_problems) doesn't show the code at HEAD, or None: its head is a commit
    in HEAD's history, and only review records (exempt) changed between that commit and HEAD (M6f, B-11)."""
    named = hold_head(text)
    sha = commit_by_prefix(root, named)
    if not sha or not is_ancestor(root, sha, head):
        return f"MERGE-HOLD-{n} names head {named}, which isn't in PR #{pr}'s history: post a new hold for head {head[:12]}"
    changed = [p for p in zsplit(git("diff", "--name-only", "--no-renames", "-z", sha, head, cwd=root).stdout)
               if not exempt(p)]
    if changed:
        shown = ", ".join(changed[:5]) + (f" and {len(changed) - 5} more" if len(changed) > 5 else "")
        return (f"MERGE-HOLD-{n} was posted for head {sha[:12]}; PR #{pr} changed since ({shown}): "
                f"post a new hold for head {head[:12]}")
    return None


def check_sensitive(g, root, head, playbook, a, room):
    rules = merge_hold_rules(playbook)
    if not rules:
        g.fail("sensitive paths", [(f"{PLAYBOOK_DIR}/PLAYBOOK.md on {STATE_BRANCH} has no merge-hold " +
                                    ("list" if rules is None else "globs") + "; the gate never runs without it",
                                    None)])
        return
    never = [glob for _, glob, _, _ in rules if glob.startswith("/") or glob.endswith("/")]
    if never:  # gitignore or CODEOWNERS style: a changed path never starts or ends with '/'
        g.fail("sensitive paths", [(f"glob can never match: {glob}", None) for glob in never])
        return
    out = zsplit(git("diff", "--name-status", "--no-renames", "-z", f"refs/remotes/origin/main...{head}",
                     cwd=root).stdout)
    changes = list(zip(out[0::2], out[1::2]))
    hits = []  # (path, why)
    for status, path in changes:
        for label, glob, deleted_only, rx in rules:
            if (status == "D" or not deleted_only) and rx.fullmatch(path):
                hits.append((path, f"{path} ({'deleted; ' if status == 'D' else ''}`{glob}`, {label})"))
                break
    if not hits:
        g.ok("sensitive paths", f"{len(changes)} changed path(s), none on the merge-hold list")
        return
    held, paths = "; ".join(why for _, why in hits), [p for p, _ in hits]
    if a.allow_hold != "5":
        g.fail("sensitive paths", [(f"on the merge-hold list: {held}", 5)])
        return
    # the decision must answer this PR's hold: the lead's MERGE-HOLD-n (same n) for reason 5, these paths
    # and a head whose code is HEAD's but for review records, posted before it and not edited since (an
    # edit keeps the comment's id), and no hold for this PR after it
    n = a.decision.rsplit("-", 1)[1]
    holds = room.holds(f"MERGE-HOLD-{n}")
    lacking = [hold_problems(m["text"], a.pr, paths) for m in holds]
    whole = [h for h, problems in zip(holds, lacking) if not problems]
    moved = {h["id"]: hold_head_problem(root, h["text"], n, a.pr, head) for h in whole}
    fresh = [h for h in whole if not moved[h["id"]]]
    decisions = room.decisions(a.decision)
    pairs = [(h, d) for h in fresh for d in decisions if room.before(h, d)]
    later = {h["id"]: room.later_hold(a.pr, h["id"]) for h, _ in pairs}  # only the newest reason-5 hold's
    pair = next(((h, d) for h, d in pairs if not later[h["id"]]), None)   # decision, not a clearing one (qodo PR #16 1)
    prefix = f"{held}; --allow-hold 5 --decision {a.decision}: "
    if pair:
        g.ok("sensitive paths", f"{held}: allowed by {a.decision} (comment #{pair[1]['id']}), answering "
                                f"MERGE-HOLD-{n} (comment #{pair[0]['id']})")
        return
    if pairs:
        newer = message_kind(later[pairs[0][0]["id"]]["text"])
        g.fail("sensitive paths", [(f"{prefix}MERGE-HOLD-{n} is not PR #{a.pr}'s newest reason-5 hold: {newer} came "
                                    "after it; use its DECISION", 5)])
        return
    edited = next((h for h in fresh for d in decisions if h["id"] < d["id"]), None)
    hold = fresh[0] if fresh else None
    others = [h for h in whole if moved[h["id"]]]  # a hold for other code: the one the decision answers, or the newest
    stale = next((h for h in others for d in decisions if room.before(h, d)), others[-1] if others else None)
    if edited:
        missing = f"MERGE-HOLD-{n} (comment #{edited['id']}) edited after {a.decision}: post a new hold"
    elif hold:
        missing = f"no trusted {a.decision} from the architect or Matthew after MERGE-HOLD-{n} (comment #{hold['id']})"
    elif stale:
        g.fail("sensitive paths", [(prefix + moved[stale["id"]], 5)])
        return
    elif holds:  # safe to show the form: a decision must still come after a new hold
        missing = (f"no MERGE-HOLD-{n} for this hold: the lead's doesn't name {', '.join(min(lacking, key=len))} "
                   f"(the form: MERGE-HOLD-<n>: PR #{a.pr}, reason 5 (sensitive paths): {', '.join(paths)}, "
                   f"head {head[:12]})")
    else:
        missing = f"no trusted MERGE-HOLD-{n} from the lead"
    g.fail("sensitive paths", [(f"{prefix}{room.where()} has {missing}", 5)])


# --- gate and merge commands

def run_gate(a, expect_sha=None):
    """The gate's checks, one line each, then the verdict. Returns (exit code, the PR's head sha or None)."""
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except AttributeError:
        pass
    if bool(a.allow_hold) != bool(a.decision):
        raise StateError("--allow-hold 5 and --decision DECISION-<n> go together")
    root = project_root()
    g = Gate()

    # 1. the PR, and its head fetched from origin
    pr = gh(f"repos/{REPO}/pulls/{a.pr}") or {}
    head = pr.get("head") or {}
    ref, sha = head.get("ref") or "", (head.get("sha") or "").lower()
    problems = []
    if pr.get("state") != "open":
        problems.append("is merged" if pr.get("merged") else f"is {pr.get('state')}, not open")
    if (pr.get("base") or {}).get("ref") != "main":
        problems.append(f"has base {(pr.get('base') or {}).get('ref')}, not main")
    head_repo = (head.get("repo") or {}).get("full_name") or ""
    if head_repo.lower() != REPO.lower():
        problems.append(f"has its head in {head_repo or 'an unknown repo'}, not {REPO}")
    m = re.fullmatch(r"mission/(M\d+)(?:-.+)?", ref)  # the mission is the token right after mission/
    if not m:
        problems.append(f"has head {ref or '?'}, not a mission/M<k>-… branch")
    elif a.mission and a.mission != m.group(1):
        problems.append(f"has head {ref}, whose mission is {m.group(1)}, not --mission {a.mission}")
    if not SHA40.fullmatch(sha):
        problems.append("has no head sha")
    if problems:
        g.fail("PR", [(f"PR #{a.pr} " + ", ".join(problems), None)])
        return g.verdict(None), None
    mission = m.group(1)
    if expect_sha and sha != expect_sha:
        print(f"✗ PR: PR #{a.pr} head is {sha}, not {expect_sha}")
        print("head moved: re-run gate")
        return EXIT_WAIT, sha
    git("fetch", "-q", "origin", f"+refs/heads/{ref}:refs/remotes/origin/{ref}",
        "+refs/heads/main:refs/remotes/origin/main", cwd=root)
    fetched = git_out("rev-parse", f"refs/remotes/origin/{ref}", cwd=root)
    if fetched != sha:
        g.fail("PR", [(f"origin's {ref} is at {fetched}, the PR's head at {sha}: it moved; run the gate again",
                       None)])
        return g.verdict(None), None
    g.ok("PR", f"PR #{a.pr} is open into main from {ref} at {sha} (mission {mission})")

    # 2. the lease
    sid = session_id(a)
    holder, gen, note = lease_holder()
    if note:
        print(f"[{note}]", file=sys.stderr)
    if holder != sid:
        print(f"✗ lease: held by {holder} (generation {gen}), not this session ({sid})")
        print("gate: lease lost")
        return EXIT_LEASE, sha
    g.ok("lease", f"held by this session ({sid}, generation {gen})")
    state = ensure_worktree()  # lease_holder just fetched it; read the pushed state, not local edits
    playbook, ledger, missions = (blob(state, STATE_REF, f"{PLAYBOOK_DIR}/{n}")
                                  for n in ("PLAYBOOK.md", "LEDGER.md", "MISSIONS.md"))

    room = RoomLog(playbook, missions)
    rec = review_records(root, sha, mission, a.pr)
    check_coverage(g, root, sha, rec)                         # 3
    try:
        phase = int(read_block(missions or "").get("phase", ""))
    except (StateError, ValueError):
        phase = None
    check_dispositions(g, root, sha, rec, ledger, room, phase)  # 4
    check_checks(g, root, sha, pr.get("updated_at"))          # 5
    check_sensitive(g, root, sha, playbook, a, room)          # 6
    return g.verdict(sha), sha


def cmd_gate(a):
    return run_gate(a)[0]


def http_status(err):
    m = re.search(r"HTTP (\d{3})", str(err))
    return int(m.group(1)) if m else 0


def cmd_merge(a):
    code, _ = run_gate(a, expect_sha=a.sha)
    if code:
        return code
    # change_state re-reads the lease right before the merge, in the same write as the intent (exit 5 if lost)
    change_state(a, f"merge: intent PR #{a.pr} at {a.sha[:12]}", lambda v: {"intent": f"merge PR #{a.pr} at {a.sha}"})

    def clear(why):
        try:
            change_state(a, f"merge: PR #{a.pr} not merged ({why})", lambda v: {"intent": "none"})
        except (StateError, StateMoved, StateExit) as e:
            print(f"[intent not cleared: {e or 'the state branch moved'}]", file=sys.stderr)

    try:
        res = gh(f"repos/{REPO}/pulls/{a.pr}/merge", "PUT", {"sha": a.sha, "merge_method": "merge"}) or {}
    except GhError as e:
        status = http_status(e)
        if status == 409:
            clear("head moved")
            print("head moved: re-run gate")
            return EXIT_WAIT
        if status == 405:
            clear("not mergeable")
            print(f"not mergeable: {e}")
            return EXIT_FAIL
        print(f"merge failed: {e}; intent left recorded for reconciliation", file=sys.stderr)
        return 1
    merged = res.get("sha") or "?"
    try:
        change_state(a, f"merge: PR #{a.pr} merged as {merged[:12]}", lambda v: {"intent": "none", "pr": f"merged:{a.pr}"})
    except (StateError, StateMoved, StateExit) as e:  # merged all the same: the intent stays for reconciliation
        print(f"merged PR #{a.pr}: {merged}; state not updated ({e or 'the state branch moved'}): reconcile")
        return 1
    print(f"merged PR #{a.pr}: {merged}")
    return 0


def mission_arg(s):
    if not re.fullmatch(r"M\d+", s):
        raise argparse.ArgumentTypeError("--mission takes M<k>, e.g. M3")
    return s


def decision_arg(s):
    if not re.fullmatch(r"DECISION-\d+", s):
        raise argparse.ArgumentTypeError("--decision takes DECISION-<n>")
    return s


def sha_arg(s):
    if not SHA40.fullmatch(s.lower()):
        raise argparse.ArgumentTypeError("--sha takes the full 40-hex head commit the gate checked")
    return s.lower()


def add_gate_commands(sub, common):
    """argparse wiring for gate and merge."""
    for name, fn, help in (
            ("gate", cmd_gate, "the merge gate: PR, lease, coverage, dispositions, checks, sensitive paths "
                               "(exit 0 pass, 3 wait, 5 lease lost, 6 fail)"),
            ("merge", cmd_merge, "run the gate, record the intent, merge naming the head sha "
                                 "(exit 3: head moved, 6: held or not mergeable)")):
        s = sub.add_parser(name, parents=[common], help=help, description=help)
        s.set_defaults(fn=state_command(fn))
        s.add_argument("pr", type=int)
        if name == "merge":
            s.add_argument("--sha", type=sha_arg, required=True, help="the head commit the gate checked")
        s.add_argument("--mission", type=mission_arg, help="M<k>: must be the mission of the head branch mission/M<k>-…")
        s.add_argument("--allow-hold", choices=("5",), help="let a sensitive-path match pass, with --decision")
        s.add_argument("--decision", type=decision_arg,
                       help="the DECISION-<n> in the room that answers the lead's MERGE-HOLD-<n> for this PR")


# --- end of review records, merge gate and merge


# --- unattended operation: watchdog, join line, handoff, reconcile, budget
#
# "Lead rotation, pausing and continuity" of docs/design/v1.md; specs docs/design/m4-unattended.md and, for
# starting leads through the lead task, docs/design/m6b-lead-relay.md. room.py supplies the facts, the text and
# the state changes around it. Every command here works inside the project's checkout or without one
# (ROOM_STATE_REMOTE).
#
#   watchdog N [--silent-after 3h]   join-line N [--takeover]
#   start-lead N ROLE [--takeover] [--force] [--seen ID] [--replacing SESSION]
#   lead-task-prompt   handoff N --step STEP --cursor ID   reconcile N   budget
#
# watchdog, reconcile and budget read the pushed state branch and never write it. The watchdog schedules nothing; it
# alarms, and after a stall's alarm starts at most one lead for it through the lead task (docs/design/m6d-watchdog.md,
# B-5).
# Intents reconcile recognizes: "merge PR #<n> at <sha>", "open PR <branch or M<k>>", "post <KIND> in room <n> after
# #<id>" and "close room <n> after #<id>" (as 'intent' records them).

WAITING_FOR_OWNER = "waiting for owner"
QUIET_STATUSES = ("paused", "stopped", "done")
PROGRESS_KEYS = ("step", "pr")  # the machine-block keys whose change is progress; merge records pr
PRESTART_HOURS = 12  # a room no lead has joined gets one alarm this long after its issue was opened
DEFAULT_BUDGET_HOURS = 8


def duration_arg(s):
    m = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", s.strip())
    secs = int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0) if m else 0
    if secs <= 0:
        raise argparse.ArgumentTypeError("a duration above zero, like 3h, 45m, 1h30m or 90s")
    return secs


def iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def parse_time(s):
    """Seconds since the epoch of an ISO-8601 time (Z, an offset, or none for UTC), or None if it isn't one."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        d = datetime.datetime.fromisoformat(s[:-1] + "+00:00" if s[-1] in "Zz" else s)
    except ValueError:
        return None
    return (d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)).timestamp()


def span(secs):
    secs = int(max(secs, 0))
    h, m = secs // 3600, secs % 3600 // 60
    return f"{h}h{m:02d}m" if h else f"{m}m" if m else f"{secs}s"


def status_of(values):
    return values.get("status") or "running"


def halted(values):
    """Whether the status is paused, stopped or done, in any case; any other value counts as running."""
    return status_of(values).strip().lower() in QUIET_STATUSES


def quiet_reason(a, values, playbook):
    """(why, text) when the watchdog stays quiet whatever the progress, or None. WHY is 'halted', 'waiting' (for
    owner, where Matthew's decision may still start a lead) or 'room' (another room); TEXT is for the quiet line."""
    room = current_room(playbook, values)
    if halted(values):
        holder, _ = lease_of(values)
        own = (values.get("room") or "").strip()
        if own.isdigit() and int(own) > 0 and room and int(own) != room[0]:
            # e.g. phase 1's DONE, while the architect has opened the next phase's room: it says nothing of this one
            print(f"note: status is {status_of(values)}, but for room {own}, not the current room {room[0]}, so it "
                  "counts as running")
        elif holder == "none":  # the lead posted PAUSED, STOPPED or DONE and released the lease
            return "halted", f"status is {status_of(values)} and the lease is released"
        else:  # written, but the lease is still held: the lead may have died before its post and release
            print(f"note: status is {status_of(values)}, but {holder} still holds the lease, so it counts as running")
    step = values.get("step") or "none"
    if step.strip().lower().startswith(WAITING_FOR_OWNER):
        holder, _ = lease_of(values)
        if holder == "none":
            return "waiting", f"step is {step}"
        # cold M6b R1-1: a lead that parks releases the lease, so a held one means a lead joined (maybe after the
        # decision) and hasn't moved on yet: it counts as running, measured from its LEAD ONLINE too
        print(f"note: step is {step}, but {holder} holds the lease, so it counts as running")
    if room and room[0] != a.room:
        return "room", (f"room {a.room} is not the current room ({room[1]} records room {room[0]}); this watchdog is "
                        "left from an earlier phase: delete it")
    return None


def say(room, role, text, a=None, buzz=None):
    """Post TEXT as ROLE through cmd_say: its role guard, its lease check on send and its buzz (BUZZ as
    --buzz/--no-buzz: None leaves it to the kind)."""
    cmd_say(argparse.Namespace(room=room, role=role, text=text, buzz=buzz, session=getattr(a, "session", None)))


def shallow_cut(path, sha):
    """Whether the state history stops at SHA only because the clone is shallow."""
    f = os.path.join(path, git_out("rev-parse", "--git-path", "shallow", cwd=path))
    try:
        with open(f) as fh:
            return sha in fh.read().split()
    except OSError:
        return False


def last_change(path, counts=lambda key: key in PROGRESS_KEYS):
    """(sha, committer time) of the newest commit on the fetched state branch whose MISSIONS.md changes a key
    of the machine block for which counts(key) holds (the commit that adds the block counts), or None. By
    default only step and pr count. A commit whose block doesn't parse changes nothing: it is skipped, so
    breaking the block is no progress. Deepens a shallow clone as far as needed."""
    rel = f"{PLAYBOOK_DIR}/MISSIONS.md"

    def value(sha):
        try:
            return {k: v for k, v in read_block(blob(path, sha, rel) or "").items() if counts(k)}
        except StateError:
            return None
    newer = None
    for _ in range(50):
        newer, oldest = None, None  # newer: (sha, time, value) of the valid commit after the one being read
        for entry in git_out("log", "--topo-order", "--format=%H %ct", STATE_REF, "--", rel, cwd=path).splitlines():
            sha, ct = entry.split()
            oldest = sha
            v = value(sha)
            if v is None:
                continue
            if newer and v != newer[2]:
                return newer[0], int(newer[1])
            newer = (sha, ct, v)
        if oldest is None or not shallow_cut(path, oldest):
            break
        before = git_out("rev-list", "--count", STATE_REF, cwd=path)
        git("fetch", "-q", "--deepen=200", "origin", f"+refs/heads/{STATE_BRANCH}:{STATE_REF}", cwd=path)
        if git_out("rev-list", "--count", STATE_REF, cwd=path) == before:
            break
    return (newer[0], int(newer[1])) if newer else None


def mission_push(heads):
    """(branch, committer time) of the newest mission/* branch tip among HEADS ({branch: sha}), or None."""
    best = None
    for branch, sha in sorted(heads.items()):
        if not branch.startswith("mission/"):
            continue
        try:
            c = gh(f"repos/{REPO}/commits/{sha}") or {}
        except GhError as e:
            if http_status(e) not in (404, 422):  # deleted after its merge since we listed it: no push to count
                raise
            continue
        t = parse_time(((c.get("commit") or {}).get("committer") or {}).get("date"))
        if t is not None and (best is None or t > best[1]):
            best = (branch, t)
    return best


def mission_branches(heads, values, missions):
    """The mission branches whose merges count: the mission/* branches on the remote, those MISSIONS.md names for
    the recorded mission (GitHub deletes a branch on merge), and the head of the recorded PR."""
    out = {b for b in heads if b.startswith("mission/")}
    mission = (values or {}).get("mission") or ""
    if re.fullmatch(r"M\d+", mission):
        out |= set(re.findall(rf"\bmission/{mission}(?:-[\w.-]+)?(?![\w.-])", missions or ""))
    n = re.search(r"\d+", (values or {}).get("pr") or "")
    if n:
        status, p = gh_try(f"repos/{REPO}/pulls/{n.group()}")
        if status == 200 and isinstance(p, dict):
            ref = (p.get("head") or {}).get("ref") or ""
            if ref.startswith("mission/"):
                out.add(ref)
        elif status not in (404, 422):
            raise GhError(f"can't read PR #{n.group()}: {p}")
    return out


def mission_merge(branches):
    """(number, merge time) of the newest merged PR from one of BRANCHES in this repo, or None. Closed PRs are
    read per branch (head=OWNER:branch), page by page, so no number of other PRs can hide a merge."""
    owner, best = REPO.split("/")[0], None
    for branch in sorted(branches):
        page = 1
        while True:
            batch = gh(f"repos/{REPO}/pulls?state=closed&head={owner}:{branch}&per_page=100&page={page}") or []
            for p in batch:
                head = p.get("head") or {}
                if head.get("ref") != branch or ((head.get("repo") or {}).get("full_name") or "").lower() != REPO.lower():
                    continue
                t = parse_time(p.get("merged_at"))
                if t is not None and (best is None or t > best[1]):
                    best = (p.get("number"), t)
            if len(batch) < 100:
                break
            page += 1
    return best


def outside_progress(values=None, missions=None):
    """[(time, what)] of the progress outside the state branch: the newest mission push and mission PR merge."""
    found, heads = [], remote_heads()
    push = mission_push(heads)
    if push:
        found.append((push[1], f"{push[0]} pushed"))
    merge = mission_merge(mission_branches(heads, values, missions))
    if merge:
        found.append((merge[1], f"PR #{merge[0]} merged"))
    return found


def watchdog_messages(a, kind, progress):
    """The room's trusted watchdog messages of KIND (LEAD-SILENT, its only kind) newer than PROGRESS (all, if None),
    oldest first."""
    out = []
    for m in map(parse, comments(a.room, iso(progress) if progress is not None else None)):
        t = parse_time(m["at"])
        if m["role"] == "watchdog" and trusted(m) and message_kind(m["text"]) == kind and t and \
                (progress is None or t > progress):
            out.append(m)
    return out


def alarms_since(a, progress, failed=False):
    """The room's trusted watchdog LEAD-SILENTs newer than PROGRESS (all, if None) whose buzz didn't fail, oldest
    first. An alarm whose buzz failed doesn't count, so it is tried again. With FAILED, every one counts (the cap)."""
    return [m for m in watchdog_messages(a, "LEAD-SILENT", progress)
            if failed or not re.search(r"\(buzz failed\b", m["text"])]


REMINDER_AFTER = 4  # a reminder once this many silent-afters have passed since the stall's last alarm
BUZZ_RETRIES = 2  # an alarm whose buzz failed is posted again at the next run, at most this many times per stall


def buzz_failed(m):
    return re.search(r"\(buzz failed\b", m["text"]) is not None


def own_alarms(a, since, only=None):
    """The stall's own trusted watchdog LEAD-SILENTs newer than SINCE (all, if None), failed buzzes included, oldest
    first; ONLY, if given, picks them."""
    return [m for m in alarms_since(a, since, failed=True) if only is None or only(m)]


def stall_alarm(a, since, first, reminder, prefix="", only=None):
    """The alarms of one stall, which SINCE identifies: its progress time, a pending DECISION's or a request's waiting
    on Matthew (None, before any lead joined: the whole room). FIRST and REMINDER are (printed line, posted text).
    The first alarm comes once. While an alarm's buzz fails, the next run posts it again, at most BUZZ_RETRIES times
    per stall (finding P); after that, and once one got through, a reminder comes every REMINDER_AFTER x silent-after
    since the stall's last alarm. ONLY, if given, picks the alarms that belong to this stall. Returns True when this
    run posted the stall's first alarm, the only run that may try a start (M6d, B-5 rule 1); a re-posted failed buzz
    or a reminder is no first alarm."""
    every = own_alarms(a, since, only)
    if not every:
        print(f"alarm: {first[0]}")
        alarm(a, first[1])
        return True
    last = every[-1]
    retries = sum(1 for prev in every[:-1] if buzz_failed(prev))  # alarms posted again after a failed buzz
    if buzz_failed(last) and retries < BUZZ_RETRIES:
        line, text = reminder if "LEAD-SILENT: still " in last["text"] else first
        print(f"alarm: {line} (again: the last buzz failed)")
        alarm(a, text)
        return False
    wait = REMINDER_AFTER * a.silent_after
    if time.time() - (parse_time(last["at"]) or 0) >= wait:
        print(f"alarm: {reminder[0]}")
        alarm(a, reminder[1])
        return False
    sent = [m for m in every if not buzz_failed(m)]
    if sent:
        print(f"quiet: {prefix}LEAD-SILENT #{sent[0]['id']} at {sent[0]['at']} already reports this stall")
    else:
        print(f"quiet: {prefix}{len(every)} alarms already posted for this stall, and none buzzed; a reminder follows "
              f"{span(wait)} after the last")
    return False


def pending_decision(a, values, playbook):
    """The trusted DECISION-n a parked lead waits on that no lead has answered: while the lease is released and room N
    is the current room, the newest DECISION (from the architect or Matthew) newer than the room's newest trusted lead
    message, a LEAD ONLINE included, and silent-after old; else None. A LEAD-STARTED after it doesn't count: if no
    lead joins, the alarm comes (BUILD-STATE 2026-11-16, B-5)."""
    room = current_room(playbook, values)
    if lease_of(values)[0] != "none" or (room and room[0] != a.room):
        return None
    msgs = [m for m in map(parse, comments(a.room)) if trusted(m)]
    last_lead = max((m["id"] for m in msgs if m["role"] == "lead"), default=0)
    now = time.time()
    found = [d for d in msgs if d["id"] > last_lead and d["role"] in ("architect", "human") and
             re.fullmatch(r"DECISION-\d+", message_kind(d["text"]) or "") and
             now - (parse_time(d["at"]) or now) >= a.silent_after]
    return found[-1] if found else None


def lead_task_ready(playbook=None):
    """Whether start-lead could fire: a token, and a lead-task: line in PLAYBOOK.md (read from the pushed state branch
    when PLAYBOOK is None)."""
    if not fire_token():
        return False
    if playbook is None:
        try:
            playbook = pushed_text(ensure_worktree(), "PLAYBOOK.md")
        except StateError:
            return False
    return bool(lead_task_id(playbook))


def try_start(a, posted_first, since, takeover, playbook, values, path, only=None):
    """After stall_alarm on the ordinary stall or the pending decision: the start rule in the run that posted the
    stall's first alarm (POSTED_FIRST, rule 1), else one note naming that alarm (M6d, B-5; qodo PR #14)."""
    if posted_first:
        start_after_alarm(a, since, takeover, playbook, values, path)
        return
    first = own_alarms(a, since, only)
    if first:
        print(f"note: no start: the watchdog tries only in the run of the stall's first alarm (#{first[0]['id']}); "
              "the architect decides")


def start_after_alarm(a, since, takeover, playbook, values, path):
    """One start per stall (M6d, B-5), only for a lead that never came, tried once: in the run whose stall_alarm, on
    the ordinary stall or the pending decision, posted the stall's first alarm, for the same SINCE (the progress time,
    or a pending DECISION's), right after it. So the alarm, posted before the fire, records the try, and a lost
    LEAD-STARTED can't lead to a second fire (qodo PR #14); a start held off, refused or failed then is never
    retried. It starts a lead as the watchdog, with --takeover when TAKEOVER (the lease is held), only when all hold,
    in order:
    (1) at the first alarm only: the caller checks it (try_start);
    (2) one start per stall: no trusted LEAD-STARTED newer than SINCE from anyone but a lead, confirmed or not; a
        lead's own handover start doesn't count, as its successor is what stalled (cold M6d R1-5, qodo PR #14);
    (3) no sign of life since SINCE: no trusted lead message newer than it from a session that hasn't handed over (a
        session's HANDOFF, what it posted before it, and its LEAD-STARTED or NEXT-LEAD-NEEDED after it don't count),
        and the lease not taken after it (held now, its newest change on the state branch at PATH older than SINCE).
        The watchdog can't tell a dead lead from one running a long foreground builder, so a lead that has spoken or
        taken the lease may be working, and the architect decides (cold M6d R2-1, R1-1, R1-4; qodo PR #14);
    (4) not halted: the machine block's status for this room isn't paused, stopped or done, whoever holds the lease,
        as a takeover would set it back to running (cold M6d R1-2);
    (5) the lead task is configured.
    Each rule that holds a start off prints a note naming why. Exit 1 from start-lead, and 3 and 6, print why; none
    is retried: the alarm and its reminders tell Matthew, and the architect decides."""
    msgs = [m for m in map(parse, comments(a.room)) if trusted(m)]

    def newer(m):
        return since is None or (parse_time(m["at"]) or 0) > since
    started = [m for m in msgs if message_kind(m["text"]) == "LEAD-STARTED" and m["role"] != "lead" and newer(m)]
    if started:
        print(f"note: LEAD-STARTED #{started[-1]['id']} at {started[-1]['at']} is this stall's start; the watchdog "
              "starts no other")
        return
    life = sign_of_life(msgs, since, values, path)
    if life:
        print(f"note: no start: a lead showed a sign of life since the stall began ({life}): it may be working; the "
              "architect decides")
        return
    own = (values.get("room") or "").strip()
    elsewhere = own.isdigit() and int(own) > 0 and int(own) != a.room
    if halted(values) and not elsewhere:  # a status recorded for another room says nothing here, as in start_refusal
        print(f"note: no start: status is {status_of(values)} (the lease is still held): the architect decides")
        return
    if not lead_task_ready(playbook):
        print("note: no start: the lead task isn't configured (no lead-task: line, or no token)")
        return
    try:
        code, why = start_lead(a, a.room, "watchdog", takeover=takeover)
    except (StateError, GhError) as e:  # reading the state or the room broke: transient
        code, why = 1, str(e)
    if code == 1:
        print(f"start failed: {why}; no retry: the alarm and its reminders tell Matthew, and the architect decides")
    elif code:
        print(f"note: no lead started: {why}")


def sign_of_life(msgs, since, values, path):
    """What shows a lead alive since SINCE, or None (M6d, B-5 rule 3): a trusted lead message newer than SINCE from a
    session that hasn't handed over, or the lease taken after SINCE. MSGS are the room's trusted messages. A session's
    HANDOFF ends it, so its HANDOFF and what it posted before, and its LEAD-STARTED or NEXT-LEAD-NEEDED after it (the
    rest of a handover), are no sign; anything else it posts after its HANDOFF is (a reused session ID). Nor is the
    lease of a session that posted a HANDOFF after taking it: it ended, even if its release failed."""
    ended = {}  # session -> ID of its newest HANDOFF
    for m in msgs:
        if m["role"] == "lead" and message_kind(m["text"]) == "HANDOFF":
            ended[m["session"]] = m["id"]
    for m in reversed(msgs):
        if m["role"] != "lead" or (parse_time(m["at"]) or 0) <= since:
            continue
        cut = ended.get(m["session"])
        if cut is not None and (m["id"] <= cut or message_kind(m["text"]) in ("LEAD-STARTED", "NEXT-LEAD-NEEDED")):
            continue
        return f"{message_kind(m['text']) or 'a message'} #{m['id']} at {m['at']} from {m['session'] or 'a lead'}"
    holder = lease_of(values)[0]
    if holder != "none":
        try:
            taken = last_change(path, lambda k: k == "lease_session")
        except StateError as e:
            return f"the lease's history can't be read ({e}), so no start this run"
        handed = [m for m in msgs if m["role"] == "lead" and m["session"] == holder
                  and message_kind(m["text"]) == "HANDOFF" and taken and (parse_time(m["at"]) or 0) > taken[1]]
        if handed:  # it handed over after taking the lease, so it has ended even if its release failed (cold M6d R3-4)
            return None
        if taken and taken[1] > since:
            return f"the lease taken by {holder} at {iso(taken[1])}, commit {taken[0][:12]}"
    return None


def waiting_request(a, values, playbook):
    """The request a parked lead waits on Matthew for (M6d, B-6): while the lease is released and room N is recorded
    as the current room, the room's newest trusted lead ESCALATION-n or MERGE-HOLD-n with no trusted DECISION-n (from
    the architect or Matthew) after it: one left open after a newer one was answered still gets its reminder (cold
    M6d R3-2), and a stale old request that a later decision made moot doesn't hide the one the lead parked on (cold
    M6d R4-2). Returns (that request, the other open requests, oldest first), which the reminder lists as also open,
    so neither order of a stale and a live request hides the live one (cold M6d S1-1); else None. Unlike
    pending_decision, a room that neither PLAYBOOK.md nor the machine block records gets no reminder (qodo PR #14)."""
    room = current_room(playbook, values)
    if lease_of(values)[0] != "none" or room is None or room[0] != a.room:
        return None
    msgs = [m for m in map(parse, comments(a.room)) if trusted(m)]
    asks = [m for m in msgs if m["role"] == "lead" and re.fullmatch(r"(?:ESCALATION|MERGE-HOLD)-\d+",
                                                                     message_kind(m["text"]) or "")]
    def answered(ask):
        n = message_kind(ask["text"]).rsplit("-", 1)[1]
        return any(m["id"] > ask["id"] and m["role"] in ("architect", "human")
                   and message_kind(m["text"]) == f"DECISION-{n}" for m in msgs)
    open_asks = [m for m in asks if not answered(m)]  # oldest first
    if not open_asks:
        return None
    return open_asks[-1], open_asks[:-1]


def alarm(a, text):
    """Buzz first (click: the room), then post TEXT saying how the buzz went, with no buzz of its own."""
    err = buzz_message(a.room, "watchdog", "LEAD-SILENT", {})
    print("[buzz sent]" if err is None else f"[buzz failed: {err}]")
    say(a.room, "watchdog", f"{text} " + ("(buzz sent)" if err is None else f"(buzz failed: {err})"), a, buzz=False)


def unreadable_state_alarm(a, path, reason):
    """No machine block anywhere, or no state branch: no lead can write state either, so the pipeline is stuck.
    The same DURATION and one alarm per stall apply, measured from the last state-branch commit, if any."""
    reason = re.sub(r"[:;] (?:the architect runs|the lead runs|run) '.*$", "", reason.replace(ME, "room.py"))[:300]
    found = outside_progress()
    if path:
        t = git("log", "-1", "--format=%ct", STATE_REF, cwd=path, check=False).stdout.strip()
        if t.isdigit():
            found.append((int(t), f"{STATE_BRANCH} commit"))
    progress, what = max(found) if found else (None, None)
    now = time.time()
    if progress is not None and now - progress < a.silent_after:
        print(f"quiet: state unreadable ({reason}), but progress {span(now - progress)} ago ({what} at "
              f"{iso(progress)}), under {span(a.silent_after)}")
        return 0
    # only the newest run of state unreadable alarms reports this stall, the ones after its last other alarm: an
    # ordinary stall alarm says nothing of the state being gone, and an outage that comes back after one gets a new
    # first alarm (qodo PR #14). Failed buzzes are retried and reminders come like any stall's (cold M6b R1-9, R3-4,
    # S4-2; M6d B-6)
    def unreadable(m):
        return re.search(r"LEAD-SILENT: (?:still )?state unreadable", m["text"]) is not None
    cut = max((m["id"] for m in alarms_since(a, progress, failed=True) if not unreadable(m)), default=0)
    stall_alarm(a, progress, (f"state unreadable ({reason})", f"LEAD-SILENT: state unreadable ({reason})"),
                (f"still state unreadable ({reason})", f"LEAD-SILENT: still state unreadable ({reason})"),
                only=lambda m: unreadable(m) and m["id"] > cut)
    return 0


def prestart_alarm(a):
    """Before any lead has joined room N (no trusted lead LEAD ONLINE there), the state may be missing or still
    the previous phase's: quiet, with a note, until PRESTART_HOURS after the room's issue was opened, then one
    alarm. Returns the exit code, or None once a lead has joined, when the usual rules apply."""
    if any(m["role"] == "lead" and trusted(m) and message_kind(m["text"]) == "LEAD ONLINE"
           for m in map(parse, comments(a.room))):
        return None
    opened = parse_time((gh(f"repos/{REPO}/issues/{a.room}") or {}).get("created_at"))
    if opened is None or time.time() - opened < PRESTART_HOURS * 3600:
        print(f"quiet: no lead has joined room {a.room} yet" +
              (f" (opened {span(time.time() - opened)} ago)" if opened is not None else ""))
        return 0
    nobody = f"no lead has joined room {a.room}"
    stall_alarm(a, None, (f"{nobody} in {PRESTART_HOURS}h (opened {iso(opened)})",
                          f"LEAD-SILENT: {nobody} in {PRESTART_HOURS}h"),
                (f"still {nobody}", f"LEAD-SILENT: still {nobody}"), prefix=f"{nobody} yet; ")
    return 0


def cmd_watchdog(a):
    code = prestart_alarm(a)  # first: before any lead joins, missing state, flags and status say nothing
    if code is not None:
        return code
    try:
        path, values, note = pushed_state()  # fetched and read from git objects: the watchdog never writes state
    except StateError as e:
        # only a state branch that ls-remote doesn't list is no state; any other failure (a fetch that broke on
        # the network) exits 1 without posting, and the next run tries again
        if STATE_BRANCH in remote_heads():
            raise StateError(f"can't read {STATE_BRANCH} ({e}); no alarm: the next run tries again")
        return unreadable_state_alarm(a, None, f"{STATE_BRANCH} doesn't exist in {REPO}")
    if not values:
        return unreadable_state_alarm(a, path, note)
    if note:  # the pushed block is damaged: the last valid one stands in
        print(f"note: {note}")
    step, mission = values.get("step") or "none", values.get("mission") or "none"
    playbook = pushed_text(path, "PLAYBOOK.md")
    quiet = quiet_reason(a, values, playbook)
    if quiet:
        why, text = quiet
        # a parked lead (lease released) and Matthew's decision that no lead has answered for silent-after: an alarm,
        # and reminders; the architect starts the lead (BUILD-STATE 2026-11-16, B-5)
        d = pending_decision(a, values, playbook) if why == "waiting" else None
        if d is None:
            # a request still waiting on Matthew: a reminder once REMINDER_AFTER x silent-after has passed since it,
            # in case its own buzz was lost, then every as long again; no start: Matthew decides (M6d, B-6)
            found = waiting_request(a, values, playbook) if why == "waiting" else None
            ask, others = found if found else (None, [])
            t = parse_time(ask["at"]) if ask else None
            if t is None or time.time() - t < REMINDER_AFTER * a.silent_after:
                print(f"quiet: {text}")
                return 0
            kind = message_kind(ask["text"])
            print(f"note: {text}, the lease is released, and {kind} #{ask['id']} at {ask['at']} has no decision yet")
            mine = f"LEAD-SILENT: still waiting for Matthew: {kind} since {iso(t)}"
            also = f" (also open: {', '.join(message_kind(m['text']) for m in others)})" if others else ""
            waiting = (f"still waiting for Matthew: {kind} since {iso(t)}{also}", f"{mine} (step {step}){also}")
            # only this request's own reminders count: a state unreadable alarm posted meanwhile doesn't delay it
            stall_alarm(a, t, waiting, waiting, only=lambda m: m["text"].startswith(mine))
            return 0
        kind, t = message_kind(d["text"]), parse_time(d["at"])
        print(f"note: {text}, the lease is released, and no lead has joined since {kind} #{d['id']} at {d['at']}")
        nobody = f"no lead joined after {kind}"
        # only this decision's own alarms count: a reminder for another request never stands in for them
        mine = re.compile(rf"LEAD-SILENT: (?:still )?{re.escape(nobody)}(?!\d)")

        def own(m):
            return mine.match(m["text"]) is not None
        posted_first = stall_alarm(a, t, (f"{nobody} ({span(time.time() - t)} ago)",
                                          f"LEAD-SILENT: {nobody} (step {step})"),
                                   (f"still {nobody}", f"LEAD-SILENT: still {nobody} (step {step})"), only=own)
        try_start(a, posted_first, t, False, playbook, values, path, only=own)  # plain: the lease is released
        return 0
    # progress, not chatter (v1): a step or pr change, a mission branch push, a mission PR's merge. Lease takes,
    # handoffs at the same step, intents, the counter and the cursor don't count, so a lead in a loop alarms
    found = outside_progress(values, pushed_text(path, "MISSIONS.md"))
    change = last_change(path)
    if change:
        found.append((change[1], f"step or pr change {change[0][:12]}"))
    if not found:
        return unreadable_state_alarm(a, path, f"{PLAYBOOK_DIR}/MISSIONS.md has no step in its history")
    progress, what = max(found)
    joined_at_wait = step.strip().lower().startswith(WAITING_FOR_OWNER) and lease_of(values)[0] != "none"
    joined = False  # a lead joined at waiting for owner: its stall is measured from its LEAD ONLINE, and only alarms
    if joined_at_wait:
        # cold M6b R1-1: measured from the later of the progress and the newest lead LEAD ONLINE, so a lead that has
        # just joined gets no alarm; the waiting_for_owner flag, set when the last lead parked, doesn't mute it
        online = newest_lead_online(a)
        if online and online[0] > progress:
            progress, what, joined = online[0], f"LEAD ONLINE #{online[1]}", True
    if (values.get("waiting_for_owner") or "").strip().lower() == "yes" and not joined_at_wait:
        # it mutes only while nothing has progressed since the commit that set it; after that it is stale
        flag = last_change(path, lambda k: k == "waiting_for_owner")
        if flag is None or progress <= flag[1]:
            print("quiet: waiting_for_owner is yes" + (f" (set at {iso(flag[1])}, no progress since)" if flag else ""))
            return 0
        print(f"note: waiting_for_owner is yes, but {what} at {iso(progress)} came after it was set at "
              f"{iso(flag[1])}, so it is stale")
    now = time.time()
    if now - progress < a.silent_after:
        print(f"quiet: progress {span(now - progress)} ago ({what} at {iso(progress)}), "
              f"under {span(a.silent_after)}")
        return 0
    about = f"step {step}, mission {mission}"
    posted_first = stall_alarm(a, progress, (f"no progress for {span(now - progress)} ({what} at {iso(progress)})",
                                             f"LEAD-SILENT: no progress since {iso(progress)} ({about})"),
                               (f"still no progress since {iso(progress)}",
                                f"LEAD-SILENT: still no progress since {iso(progress)} ({about})"))
    if joined:
        # each lead started there would begin a new stall, so starts would chain without bound (cold M6d R2-4)
        print("note: no start: a lead joined at waiting for owner; the architect decides")
        return 0
    try_start(a, posted_first, progress, lease_of(values)[0] != "none", playbook, values, path)
    return 0


def newest_lead_online(a):
    """(time, comment ID) of room N's newest trusted lead LEAD ONLINE, or None."""
    best = None
    for m in map(parse, comments(a.room)):
        t = parse_time(m["at"])
        if m["role"] == "lead" and trusted(m) and message_kind(m["text"]) == "LEAD ONLINE" and t is not None and \
                (best is None or m["id"] > best[1]):
            best = (t, m["id"])
    return best


def pinned_version(path=None):
    """The pipeline version PLAYBOOK.md pins on the state branch, else VERSION: sessions run the pinned tag,
    and links name it (v1.md, "Versioning and upgrades"), so a pin bumped mid-mission reaches the next lead."""
    try:
        if path is None:
            path = ensure_worktree()  # fetched
        m = re.search(r"^pipeline:[ \t]*(\S+)", pushed_text(path, "PLAYBOOK.md") or "", re.M)
    except StateError as e:
        print(f"[can't read the pinned version ({e}); using {VERSION}]", file=sys.stderr)
        return VERSION
    if m and re.fullmatch(r"v\d+(\.\d+)*(-[\w.]+)?|main", m.group(1)):
        return m.group(1)
    print(f"[PLAYBOOK.md pins no pipeline version; using {VERSION}]", file=sys.stderr)
    return VERSION


TAKEOVER_SENTENCE = " Take over the lease (lease take --takeover): the previous lead stopped without handing over."


def join_text(room, version, takeover=False):
    """The join line for ROOM at VERSION. The lead task's prompt is built from it with <N> and <V>, so the two
    can't drift apart."""
    line = f"Join agent room {room} in {REPO} as lead, pipeline {version}. Follow LEAD.md: {doc_url('LEAD.md', version)}"
    return line + (TAKEOVER_SENTENCE if takeover else "")


def join_line(room, takeover=False, version=None):
    return join_text(room, version or pinned_version(), takeover)


def cmd_join_line(a):
    version = pinned_version()
    text = join_line(a.room, a.takeover, version=version)
    rejected = pin_rejected(version, text)  # the architect fires this line: the lead task would end at once
    if rejected:
        print(rejected, file=sys.stderr)
        return EXIT_NOT_CONFIGURED
    print(text)


def cmd_handoff(a):
    sid = session_id(a)
    step = single_line("--step", a.step)
    if not step:
        raise StateError("--step needs the step the successor starts at")
    path = ensure_worktree()  # fetched
    p = pending(path)
    if p:  # change_state would refuse after HANDOFF is posted; refuse before it instead
        raise StateError(f"not handed off: the state worktree {path} has {p}: push them with '{ME} state commit "
                         f"-m MSG', or drop them with '{ME} state sync'")
    values, note = pushed_lease(path)  # the last valid block when the pushed one is damaged
    if note:
        print(f"[{note}]", file=sys.stderr)
    require_lease(values, sid, "not handed off")
    # the last comment the lead acted on, which it names: the cursor file also moves when the waiter merely reads
    cursor = a.cursor
    if cursor != "none":
        try:
            c = gh(f"repos/{REPO}/issues/comments/{cursor}") or {}
        except GhError as e:
            raise StateError(f"not handed off: --cursor {cursor}: {e}")
        if not (c.get("issue_url") or "").endswith(f"/issues/{a.room}"):
            raise StateError(f"not handed off: --cursor {cursor} is not a comment of room {a.room}")
    # (a) record step, cursor and intent=none, holding the lease; (b) post HANDOFF, still holding it; (c) release it.
    # If (a) fails, nothing is posted; if (c) fails, the room has the HANDOFF and the lead must release by hand.
    def write(msg, updates):
        for attempt in (1, 2, 3):
            try:
                return change_state(a, msg, lambda v: updates)
            except StateMoved:  # someone else wrote the state branch meanwhile: re-read, re-check the lease, re-apply
                if attempt == 3:
                    raise
            except StateError:
                reset_to_remote(path)  # drop the unpushed commit, so the next try starts clean
                raise
    try:
        write(f"handoff: {sid} records step {step} for its successor",
              {"step": step, "cursor": cursor, "intent": "none"})
    except StateMoved:
        raise StateExit(EXIT_MOVED, f"not handed off: {STATE_BRANCH} kept moving, so nothing was posted; run "
                                    "handoff again")
    say(a.room, "lead", f"HANDOFF: mission {values.get('mission') or 'none'}, next step {step}\n\n"
                        "The successor is being started through the lead task; NEXT-LEAD-NEEDED follows if that "
                        "fails.", a)
    try:
        write(f"handoff: {sid} releases the lead lease", {"lease_session": "none"})
    except (StateError, StateMoved, StateExit) as e:
        print(f"lease not released: {str(e) or f'{STATE_BRANCH} kept moving'}", file=sys.stderr)
        print(f"HANDOFF is posted; run '{ME} lease release' again", file=sys.stderr)
        return 1
    print(f"recorded step {step}, cursor {cursor}, intent none; lease released by {sid}")
    version = pinned_version(path)
    text = join_line(a.room, version=version)
    rejected = pin_rejected(version, text)  # the handoff is done either way; only the line would be useless
    print(f"Start the successor: {ME} start-lead {a.room} lead --repo {REPO}. If it exits 6, or 1 twice: "
          f"{ME} say {a.room} lead 'NEXT-LEAD-NEEDED: ...' --repo {REPO}." +
          ("" if rejected else " The join line, for a start by hand:"))
    if rejected:
        print(rejected, file=sys.stderr)
    else:
        print(text)


def is_merged(p):
    return bool(p.get("merged") or p.get("merged_at"))


def pr_state(p):
    if is_merged(p):
        return f"merged as {p.get('merge_commit_sha') or '?'}"
    if p.get("state") == "open":
        return f"open at {(p.get('head') or {}).get('sha') or '?'}"
    return "closed without merging"


def pr_problem(p):
    """Why reconcile doesn't count PR object P as the lead's, or None. On a public repo anyone can open a PR,
    even from a branch named like the mission's: it counts only from this repo, by a trusted author, into main."""
    head_repo = ((p.get("head") or {}).get("repo") or {}).get("full_name") or ""
    author = (p.get("user") or {}).get("login") or ""
    if head_repo.lower() != REPO.lower():
        return f"its head is in {head_repo or 'an unknown repo'}, not {REPO}"
    if author.lower() not in TRUST:
        return f"its author {author or '?'} is not trusted"
    if (p.get("base") or {}).get("ref") != "main":
        return f"its base is {(p.get('base') or {}).get('ref') or '?'}, not main"
    return None


def pull_requests():
    out, page = [], 1
    while True:
        batch = gh(f"repos/{REPO}/pulls?state=all&per_page=100&page={page}") or []
        out += batch
        if len(batch) < 100:
            return out
        page += 1


def intent_hint(a, intent, path, msgs, pr):
    """The one-line verdict on a recorded intent: done (clear it), not done (redo it), or unknown."""
    leads = [m for m in msgs if m["role"] == "lead"]
    m = re.fullmatch(r"merge PR #(\d+) at ([0-9a-fA-F]{7,40})", intent)
    if m:
        n, p = m.group(1), pr(int(m.group(1)))
        if p is None:
            return f"intent unknown: PR #{n} can't be read; check it by hand"
        if pr_problem(p):
            return f"intent unknown: PR #{n} doesn't count ({pr_problem(p)}); check it by hand"
        if is_merged(p):
            return f"intent done: clear it (PR #{n} is {pr_state(p)}; finish the bookkeeping)"
        if p.get("state") == "open":
            return f"intent not done: redo it (PR #{n} is {pr_state(p)}; run the gate, then merge)"
        return (f"intent not done: PR #{n} was closed without merging, so it can't be merged: clear the intent, "
                "and reopen the PR or escalate")
    m = re.fullmatch(r"open PR (?:for |from )?(\S+)", intent)
    if m:
        ref = m.group(1)
        want = re.compile(re.escape(ref) if ref.startswith("mission/") else rf"mission/{re.escape(ref)}(?:-.+)?")
        named = [p for p in pull_requests() if want.fullmatch((p.get("head") or {}).get("ref") or "")]
        hits = [p for p in named if not pr_problem(p)]
        ignored = f"; ignored {len(named) - len(hits)} from another repo or author" if len(named) > len(hits) else ""
        live = [p for p in hits if is_merged(p) or p.get("state") == "open"]
        if live:
            p = max(live, key=lambda p: p.get("number", 0))
            return f"intent done: clear it (PR #{p.get('number')} from {p['head']['ref']} is {pr_state(p)}; record it)"
        if hits:
            p = max(hits, key=lambda p: p.get("number", 0))
            return (f"intent not done: redo it (PR #{p.get('number')} from {p['head']['ref']} was closed without "
                    f"merging; open a new one{ignored})")
        return f"intent not done: redo it (no PR from {ref}{ignored})"
    m = re.fullmatch(r"post (.+?)(?: in room (\d+))?(?: after #(\d+))?", intent)
    kind = message_kind(m.group(1)) if m else None
    if kind:
        # 'intent' records the room and its last comment ID: a later trusted lead message of the kind in that room
        # did it. Without an ID, only a numbered kind, unique in the room, can be judged. No clocks involved.
        where = int(m.group(2)) if m.group(2) else a.room
        after = int(m.group(3)) if m.group(3) else None
        if after is None and not re.search(r"-\d+$", kind):
            return (f"intent unknown: which {kind}? Record post intents with '{ME} intent N \"post {kind}\"', "
                    "which notes the room's last comment")
        if where != a.room:
            leads = [x for x in map(parse, comments(where)) if trusted(x) and x["role"] == "lead"]
        place = f"room {where}" if m.group(2) else "the room"
        hits = [x for x in leads if message_kind(x["text"]) == kind and (after is None or x["id"] > after)]
        if hits:
            return f"intent done: clear it ({kind} is in {place}: #{hits[-1]['id']})"
        return f"intent not done: redo it (no {kind} in {place}" + (f" after #{after})" if after is not None else ")")
    m = re.fullmatch(r"close (?:the )?room(?: (\d+))?(?: after #(\d+))?", intent)
    if m:
        if m.group(1) and int(m.group(1)) != a.room:  # e.g. phase 1's DONE, still in the block in phase 2
            return f"intent from an earlier room: clear it (close room {m.group(1)}; this is room {a.room})"
        issue = gh(f"repos/{REPO}/issues/{a.room}") or {}
        if issue.get("state") != "closed":
            return f"intent not done: redo it (room {a.room} is open)"
        closes = [x for x in leads if message_kind(x["text"]) in ("DONE", "STOPPED")]
        if m.group(2):
            # 'intent' recorded the room's last comment: a later trusted lead DONE or STOPPED is the closing note,
            # posted before the close (as the protocol does) or after it (as close does with a text)
            after = int(m.group(2))
            notes, since = [x for x in closes if x["id"] > after], f"after #{after}"
        else:  # recorded without an ID: the note close posts after closing
            closed = parse_time(issue.get("closed_at"))
            notes = [x for x in closes if closed is not None and (parse_time(x["at"]) or 0) >= closed]
            since = "came after it closed"
        if notes:
            kind = message_kind(notes[-1]["text"])
            return f"intent done: clear it (room {a.room} is closed, closing {kind} #{notes[-1]['id']})"
        return f"intent not done: redo it (room {a.room} is closed, but no lead DONE or STOPPED {since})"
    return ("intent unknown: check it by hand (reconcile knows: merge PR #<n> at <sha>, open PR <branch or M<k>>, "
            "post <KIND>, close room)")


def cmd_intent(a):
    """Record before acting: the intent, in its own state write, for room N, which must be the current room. A
    post intent also records the room and its last comment ID (post KIND in room N after #ID), so reconcile can
    tell a later post of that kind from an earlier one, in the right room."""
    text = single_line("intent", a.intent)
    if not text:
        raise StateError("say what is about to happen (merge PR #<n> at <sha>, open PR <branch>, post <KIND>, "
                         "close room), or none")
    path, values, _ = pushed_state()
    found = current_room(pushed_text(path, "PLAYBOOK.md"), values)
    if found and found[0] != a.room:
        raise StateError(f"not recorded: room {a.room} is not the current room ({found[1]} records room "
                         f"{found[0]})")
    m = re.fullmatch(r"post\s+(.+)", text)
    if m:
        kind = message_kind(m.group(1))
        if not kind:
            raise StateError(f"a post intent names the message kind: post ESCALATION-3, post PAUSED…, not {text!r}")
        text = f"post {kind} in room {a.room} after #{max((c['id'] for c in comments(a.room)), default=0)}"
    elif re.fullmatch(r"close (?:the )?room(?: \d+)?(?: after #\d+)?", text):
        # with its room, so that left in the block after DONE it can't send the next phase to close its own room,
        # and with the room's last comment, so that a DONE posted before the close counts
        text = f"close room {a.room} after #{max((c['id'] for c in comments(a.room)), default=0)}"
    change_state(a, f"intent: {text}", lambda v: {"intent": text})
    print(f"intent: {text}")


def cmd_reconcile(a):
    path, values = recorded_state()  # it changes nothing: no state write, no cursor move
    print(f"recorded state ({PLAYBOOK_DIR}/MISSIONS.md on {STATE_BRANCH} at "
          f"{git_out('rev-parse', '--short', STATE_REF, cwd=path)}):")
    for k, v in values.items():
        print(f"  {k}: {v}")
    cache = {}

    def pr(n):
        if n not in cache:
            try:
                cache[n] = gh(f"repos/{REPO}/pulls/{n}") or {}
            except GhError as e:
                print(f"[can't read PR #{n}: {e}]", file=sys.stderr)
                cache[n] = None
        return cache[n]

    recorded = values.get("pr") or "none"
    n = re.search(r"\d+", recorded) if recorded != "none" else None
    if n:
        p = pr(int(n.group()))
        print(f"PR: #{n.group()} " + ("unreadable" if p is None else
                                      f"ignored: {pr_problem(p)}" if pr_problem(p) else pr_state(p)))
    else:
        print("PR: none recorded")

    msgs = [m for m in map(parse, comments(a.room)) if trusted(m)]

    def latest(roles, kinds):
        hits = [m for m in msgs if m["role"] in roles and message_kind(m["text"]) in kinds]
        return hits[-1] if hits else None

    try:
        counter = int(values.get("counter") or 0)
    except ValueError:
        counter = 0
    if counter > 0:
        held = latest(("lead",), (f"ESCALATION-{counter}", f"MERGE-HOLD-{counter}"))
        if held:
            answer = latest(("architect", "human"), (f"DECISION-{counter}",))
            print(f"counter {counter}: {message_kind(held['text'])} is in the room (#{held['id']}), " +
                  (f"answered by DECISION-{counter} (#{answer['id']})" if answer else f"no DECISION-{counter} yet"))
        else:
            print(f"counter {counter}: neither ESCALATION-{counter} nor MERGE-HOLD-{counter} is in the room")
    else:
        print("counter 0: no escalation or hold yet")

    h = latest(("lead",), ("HANDOFF",))
    if h:
        first = h["text"].splitlines()[0]
        named = re.search(r"next step (.+)$", first)
        step = values.get("step") or "none"
        note = "names the recorded step" if named and named.group(1).strip() == step else \
            f"the recorded step is {step}"
        online = [m for m in msgs if m["role"] == "lead" and m["id"] > h["id"] and message_kind(m["text"]) == "LEAD ONLINE"]
        if online:
            note += f"; LEAD ONLINE #{online[-1]['id']} came after it"
        print(f"HANDOFF: #{h['id']} at {h['at']} from lead · {h['session'] or '?'}: {first} ({note})")
    else:
        print("HANDOFF: none in the room")

    intent = values.get("intent") or "none"
    print(f"intent: {intent}")
    if intent != "none":
        print(intent_hint(a, intent, path, msgs, pr))
    if halted(values):
        print(f"status: {status_of(values)}: lease take sets it back to running when a lead resumes the work")
    drill = re.search(r"^drill:[ \t]*(\S.*?)[ \t]*$", pushed_text(path, "PLAYBOOK.md") or "", re.M)
    if drill:
        print(f"drill: {drill.group(1)}")
    return 0


def phase_budget(playbook, phase):
    """(hours, source) of the "Mission budget: <n> hours" phrase under PLAYBOOK.md's "### Phase <phase>:"
    heading, else the default eight hours."""
    m = re.search(rf"^###[ \t]+Phase[ \t]+{re.escape(phase)}:[^\n]*\n(.*?)(?=^#{{1,3}}[ \t]|\Z)", playbook or "",
                  re.M | re.S)
    # tolerant: markdown emphasis around the label or the number; h, hr, hrs, hour or hours; decimals
    b = re.search(r"mission budget[*_` \t]*:[*_` \t]*(\d+(?:\.\d+)?|\.\d+)[*_` \t]*(?:hours?|hrs?|h)(?![a-z])",
                  m.group(1), re.I) if m else None
    if b and float(b.group(1)) > 0:
        return float(b.group(1)), f"phase {phase} in PLAYBOOK.md"
    return float(DEFAULT_BUDGET_HOURS), "the default"


def cmd_budget(a):
    path, values = recorded_state()
    mission, phase = values.get("mission") or "none", values.get("phase") or "1"
    started = values.get("mission_started") or "none"
    if started == "none":
        print(f"budget: mission_started is none (mission {mission}); record it with the mission's spec: "
              f"'{ME} state set mission_started={iso(time.time())}'")
        return 1
    t0 = parse_time(started)
    if t0 is None:
        raise StateError(f"mission_started is {started!r}, not an ISO-8601 time")
    hours, source = phase_budget(pushed_text(path, "PLAYBOOK.md"), phase)
    elapsed, budget = time.time() - t0, hours * 3600
    line = f"budget: mission {mission} started {iso(t0)}, {span(elapsed)} elapsed of {hours:g}h ({source})"
    if elapsed > budget:
        print(f"{line}: over by {span(elapsed - budget)}; post an ESCALATION, never another automatic retry")
        return EXIT_FAIL
    print(f"{line}: {span(budget - elapsed)} left")
    return 0


# --- the lead task: one scheduled task per project, started through its API trigger (M6b)
#
# Matthew creates it once in the web UI, with lead-task-prompt's text as its prompt, and puts its token in the
# agent-room environment as ROOM_FIRE_TOKEN_<NAME> (else ROOM_FIRE_TOKEN); the architect records its ID in
# PLAYBOOK.md as `lead-task: trig_…`. start-lead POSTs the join line as the run's text. The token is sent in a
# header, as buzz sends ntfy's, and scrubbed from everything printed, returned or posted.

FIRE_URL = "https://api.anthropic.com"
FIRE_BETA = "experimental-cc-routine-2026-04-01"
FIRE_TIMEOUT = 30  # seconds for the whole request
STARTING_FOR = 30 * 60  # a LEAD-STARTED this recent with no LEAD ONLINE after it: a lead is still starting (30
                        # minutes, the window ARCHITECT.md gives the architect: cold M6b R1-7, R2-1)
LEAD_TASK = re.compile(r"^lead-task:[ \t]*(trig_[A-Za-z0-9]+)", re.M)
SETUP_PAGE = "docs/manual/set-up-the-lead-task.md"
START_ROLES = ("lead", "watchdog", "architect")  # the watchdog starts one lead per stall (M6d, B-5)
EXIT_REFUSED, EXIT_NOT_CONFIGURED = 3, 6
LEAD_TASK_PROMPT = (
    "You are a lead session of the agent-room pipeline for {repo}. This run was started with your join line as its "
    "text: in a routine-fire-payload block, or as a message after this prompt. The pipeline's own room.py sent it, "
    "and this prompt authorizes you to act on it, but only if the whole text has exactly this form:\n\n"
    "{join}\n\n"
    "optionally followed by exactly this sentence:\n\n"
    "{takeover}\n\n"
    "Here <N> is a number, and <V> is main or a version such as v1.0.0, the same in both places. If the text has "
    "that form, carry out the join line as if Matthew had sent it to you. If there is no such text, or it differs in "
    "any way, end at once without running anything or posting anything.")


def prompt_form():
    """The join-line form the lead task's prompt accepts, as a regex built from the same join_text: <N> a number, <V>
    main or v followed by dot-separated numbers, the same in both places, optionally the takeover sentence."""
    form = re.escape(join_text("<N>", "<V>")).replace(re.escape("<N>"), r"\d+")
    form = form.replace(re.escape("<V>"), r"(main|v\d+(?:\.\d+)*)", 1).replace(re.escape("<V>"), r"\1")
    return re.compile(form + f"(?:{re.escape(TAKEOVER_SENTENCE)})?")


def pin_rejected(version, text=None):
    """Why the lead task's prompt would reject the join line pinned to VERSION (TEXT, else a sample join line), or
    None. start-lead, join-line, handoff and preflight all check pins here (cold M6b R1-6)."""
    if prompt_form().fullmatch(text if text is not None else join_text(1, version)):
        return None
    return f"pin {version} isn't accepted by the lead task's prompt: pin main or a release vX.Y.Z"


def lead_task_id(playbook):
    """The lead task's ID from PLAYBOOK.md's `lead-task:` line, or None."""
    m = LEAD_TASK.search(playbook or "")
    return m.group(1) if m else None


def fire_token_var():
    """ROOM_FIRE_TOKEN_<NAME>: the repo's name in upper case, every character other than A-Z and 0-9 as _."""
    return "ROOM_FIRE_TOKEN_" + re.sub(r"[^A-Z0-9]", "_", REPO.split("/")[1].upper())


def fire_token():
    """The lead task's token: ROOM_FIRE_TOKEN_<NAME>, else ROOM_FIRE_TOKEN; None if neither is set."""
    for var in (fire_token_var(), "ROOM_FIRE_TOKEN"):
        value = os.environ.get(var, "").strip()
        if value:
            return value
    return None


def one_line(text, token, limit=300):
    """TEXT on one line, at most LIMIT characters, with the token scrubbed."""
    return " ".join(scrub(str(text), (token,)).split())[:limit]


UNSURE_CURL_EXITS = {8, 16, 18, 28, 52, 55, 56, 92}  # curl gave up after the request may have reached the API: a weird
# reply, broken HTTP/2 framing, a timeout, a partial, empty or lost reply, a broken send or stream (cold M6b S2-5).
# Any other curl failure (no DNS, no connection) is definite.
UNSURE_STATUSES = {200, 502, 504}  # 200 without routine_fire, and a gateway's errors, which can come after the API fired


def fire(task, token, text):
    """POST {"text": TEXT} to lead task TASK's fire endpoint. Returns (HTTP status, answer): the parsed JSON body,
    else its text; or (0, why) when curl failed before the request could reach the API, and (-1, why) when it failed
    after, so a lead may have started (qodo PR #11). Never raises; no error holds the token or curl's argv."""
    base = (os.environ.get("ROOM_FIRE_URL", "").strip() or FIRE_URL).rstrip("/")
    beta = os.environ.get("ROOM_FIRE_BETA", "").strip() or FIRE_BETA
    # the token goes through stdin, as a curl config line, never in argv where any process can read it (qodo PR #11)
    quoted = token.replace("\\", "\\\\").replace('"', '\\"')
    cmd = ["curl", "-sS", "-m", str(FIRE_TIMEOUT), "-X", "POST", "--config", "-",
           "-H", f"anthropic-beta: {beta}", "-H", "anthropic-version: 2023-06-01", "-H", "Content-Type: application/json",
           "--data-raw", json.dumps({"text": text}), "-w", "\n%{http_code}",
           f"{base}/v1/claude_code/routines/{task}/fire"]
    try:
        r = subprocess.run(cmd, input=f'header = "Authorization: Bearer {quoted}"\n', capture_output=True, text=True,
                           errors="replace", timeout=FIRE_TIMEOUT + 5)
    except subprocess.TimeoutExpired:  # its text would hold the whole argv, token included
        return -1, f"curl timed out after {FIRE_TIMEOUT}s"
    except OSError as e:  # its text can hold a file name; strerror doesn't
        return 0, f"could not run curl: {e.strerror or type(e).__name__}"
    if r.returncode != 0:
        why = one_line(r.stderr.strip(), token) or f"curl exited {r.returncode}"
        return (-1 if r.returncode in UNSURE_CURL_EXITS else 0), why
    body, _, status = r.stdout.rpartition("\n")
    if not status.strip().isdigit():
        return 0, "curl gave no HTTP status"
    try:
        answer = json.loads(body) if body.strip() else None
    except ValueError:
        answer = body
    return int(status), answer


def answer_detail(answer, token):
    """A short, scrubbed line from an error answer, or ''."""
    if isinstance(answer, dict):
        err = answer.get("error")
        text = (err.get("message") if isinstance(err, dict) else None) or answer.get("message") or json.dumps(answer)
    else:
        text = answer or ""
    return one_line(text, token)


def session_url(answer, token):
    """The started session's URL from a routine_fire answer, checked to be one plain https link."""
    url = answer.get("claude_code_session_url")
    if isinstance(url, str) and re.fullmatch(r"https://[^\s<>()\[\]`]{1,300}", url):
        return scrub(url, (token,))
    sid = answer.get("claude_code_session_id")
    if isinstance(sid, str) and re.fullmatch(r"[\w-]{1,100}", sid):
        return scrub(f"https://claude.ai/code/{sid}", (token,))
    return "(no session URL in the answer)"


def start_refusal(room, role, takeover, force, values, playbook, sid=None):
    """Why start-lead won't start a lead in ROOM as ROLE, or None (M6b's guards, in order)."""
    found = current_room(playbook, values)
    if found and found[0] != room:
        return f"room {room} is not the current room ({found[1]} records room {found[0]})"
    if is_closed(room):
        return f"room {room} is closed"
    status, holder = status_of(values).strip().lower(), lease_of(values)[0]
    own = (values.get("room") or "").strip()
    # a status recorded for another room says nothing here; a halted one with the lease still held counts as running,
    # as in M4: the lead may have died between writing it and posting (cold M6b R1-5)
    here = not (own.isdigit() and int(own) > 0 and int(own) != room)
    if here and holder == "none":
        if status == "done":
            return "status is done and the lease is released: the phase is over"
        if status in ("paused", "stopped") and role != "architect":
            return f"status is {status} and the lease is released: only the architect resumes, on Matthew's word"
    if here and holder != "none" and takeover and status in ("paused", "stopped") and not force:
        # the takeover lead's lease take --takeover would set the status back to running, for any role (cold M6d R3-3)
        return (f"status is {status} with the lease still held: a takeover would set it back to running; on "
                "Matthew's word to resume, add --force")
    if holder != "none" and not takeover:
        if holder == sid:  # e.g. a handoff whose release failed (cold M6b R2-4)
            return "this session still holds the lease: run lease release, then start-lead again"
        return (f"the lease is held by {holder}: a lead is running, and a takeover (--takeover) is the architect's or, "
                "once per stall, the watchdog's call")
    if not force:
        msgs = [m for m in map(parse, comments(room)) if trusted(m)]
        online = max((m["id"] for m in msgs if m["role"] == "lead" and message_kind(m["text"]) == "LEAD ONLINE"),
                     default=0)
        now = time.time()
        recent = [m for m in msgs if m["id"] > online and message_kind(m["text"]) == "LEAD-STARTED"
                  and now - (parse_time(m["at"]) or 0) < STARTING_FOR]
        if recent:
            m = recent[-1]
            return (f"LEAD-STARTED #{m['id']} at {m['at']} ({span(now - parse_time(m['at']))} ago) has no LEAD ONLINE "
                    f"after it: a lead is still starting (--force starts another)")
    return None


POST_RETRY_WAITS = (2, 5)  # seconds before the second and third try of a LEAD-STARTED post (qodo PR #11)


def already_posted(room, role, text, a):
    """Whether room ROOM's comments of the last ten minutes hold TEXT from this ROLE and session, trusted. A read
    that fails counts as no."""
    sid = session_id(a)
    try:
        recent = [parse(c) for c in comments(room, iso(time.time() - 600))]
    except GhError:
        return False
    return any(m["role"] == role and m["session"] == sid and m["text"] == text.strip() and trusted(m) for m in recent)


def post_quietly(room, role, text, a):
    """Post TEXT as ROLE through say (its role guard and lease check on send), with no buzz. A failed post is tried
    twice more, after POST_RETRY_WAITS, since the start it records has happened; a refusal isn't. Returns None, or why
    it wasn't posted; never exits."""
    for wait in (*POST_RETRY_WAITS, None):
        try:
            say(room, role, text, a, buzz=False)
            return None
        except SystemExit as e:  # the role guard or the lease check refused it, and said why on stderr
            return e.code if isinstance(e.code, str) else f"refused (exit {e.code})"
        except (GhError, StateError) as e:
            if wait is None:
                return str(e)
            print(f"[LEAD-STARTED not posted ({e}); trying again in {wait}s]", file=sys.stderr)
            time.sleep(wait)
            if already_posted(room, role, text, a):  # GitHub may have made it and lost the answer (cold M6b S2-4)
                print("[it was posted after all]", file=sys.stderr)
                return None


def room_moved_on(room, seen):
    """Why the room moved on after comment SEEN, or None: its first trusted lead message, or trusted LEAD-STARTED from
    any role, with a larger comment ID (cold M6d R1-1)."""
    for m in map(parse, comments(room)):
        if m["id"] > seen and trusted(m) and (m["role"] == "lead" or message_kind(m["text"]) == "LEAD-STARTED"):
            return (f"the room moved on after #{seen}: {message_kind(m['text']) or 'a message'} #{m['id']} at "
                    f"{m['at']}; read the room again")
    return None


def lease_moved(values, replacing):
    """Why a takeover replacing session REPLACING is out of date, or None: the lease in VALUES isn't held by it."""
    holder = lease_of(values)[0]
    if holder == replacing:
        return None
    now = "released" if holder == "none" else f"held by {holder}"
    return f"the lease is now {now}, not held by {replacing}; read the room again"


def start_lead(a, room, role, takeover=False, force=False, seen=None, replacing=None):
    """Start a lead in ROOM through the lead task, as ROLE: read the configuration, check the guards, POST the join
    line, then post LEAD-STARTED. Returns (exit code, why): 0 started, or maybe started (an unconfirmed LEAD-STARTED;
    why None), 1 a definite failure (try once more), 3 refused, 6 not configured or rejected. ROLE is the lead (its
    handover), the architect, or the watchdog (one start per stall, M6d). SEEN, a comment ID: refuse when the room
    moved on after it (an architect's starter task, which may run hours after it was made). A broken read of the
    state branch or the room raises StateError or GhError. REPLACING, a session, with TAKEOVER: refuse unless the
    lease is still held by it, the lead the architect decided to take over (cold M6d R3-1)."""
    try:
        path = ensure_worktree()  # fetched
    except StateError:
        if STATE_BRANCH in remote_heads():
            raise  # it exists, so the read broke: transient
        path = None  # no state branch, so no PLAYBOOK.md
    playbook = pushed_text(path, "PLAYBOOK.md") if path else None
    values = pushed_lease(path)[0] if path else {}
    task, token = lead_task_id(playbook), fire_token()
    missing = []
    if not task:
        missing.append(f"PLAYBOOK.md on {STATE_BRANCH} has no lead-task: line" if path else
                       f"{STATE_BRANCH} doesn't exist in {REPO}, so PLAYBOOK.md has no lead-task: line")
    if not token:
        missing.append(f"neither {fire_token_var()} nor ROOM_FIRE_TOKEN is set")
    if missing:
        page = doc_url(SETUP_PAGE, pinned_version(path) if path else None)
        return EXIT_NOT_CONFIGURED, f"not configured: {'; '.join(missing)}. See Set up the lead task: {page}"
    why = start_refusal(room, role, takeover, force, values, playbook, session_id(a))
    if why is None and seen is not None:
        why = room_moved_on(room, seen)
    if why is None and replacing is not None:
        why = lease_moved(values, replacing)
    if why:
        return EXIT_REFUSED, f"refused: {why}"
    version = pinned_version(path)
    text = join_line(room, takeover, version=version)
    rejected = pin_rejected(version, text)  # a pre-release pin: the started session would end at once (cold M6b R1-6)
    if rejected:
        return EXIT_NOT_CONFIGURED, rejected
    status, answer = fire(task, token, text)
    by = f"started by {role}"
    if status == 200 and isinstance(answer, dict) and answer.get("type") == "routine_fire":
        url = session_url(answer, token)
        print(f"started: {url}")
        err = post_quietly(room, role, f"LEAD-STARTED: {url} ({'takeover' if takeover else 'plain'} join line, {by})",
                           a)
        if err:
            print(f"started, but LEAD-STARTED wasn't posted: {one_line(err, token)}")
        return 0, None
    if status == -1 or status in UNSURE_STATUSES:
        # the outcome is unknown: a lead may have started, so a retry could start a second one (qodo PR #11). Record
        # it as unconfirmed, so a by-hand start waits for it, and a LEAD ONLINE follows if one started
        reason = one_line(answer, token, 200) if status == -1 else \
            "HTTP 200 without routine_fire" if status == 200 else f"HTTP {status}"
        print(f"warning: the lead task may have started a lead ({reason}); recorded as unconfirmed, not retried")
        err = post_quietly(room, role, f"LEAD-STARTED: unconfirmed ({reason}); a LEAD ONLINE follows if the lead "
                                       f"started ({by})", a)
        if err:
            print(f"LEAD-STARTED wasn't posted: {one_line(err, token)}")
        return 0, None
    if status in (401, 403):
        return EXIT_NOT_CONFIGURED, f"token rejected (HTTP {status})"
    if status == 404:
        return EXIT_NOT_CONFIGURED, f"lead task {task} not found"
    if status == 0:
        return 1, f"lead task not started: {answer}"
    detail = answer_detail(answer, token)
    return 1, f"lead task not started: HTTP {status}" + (f": {detail}" if detail else "")


def cmd_start_lead(a):
    if a.replacing is not None and not a.takeover:
        print("room.py start-lead: error: --replacing SESSION goes with --takeover: it names the lead a takeover "
              "replaces", file=sys.stderr)
        return 2
    code, why = start_lead(a, a.room, a.role, a.takeover, a.force, a.seen, a.replacing)
    if why:
        print(why, file=sys.stderr)
    return code


def cmd_lead_task_prompt(a):
    print(LEAD_TASK_PROMPT.format(repo=REPO, join=join_text("<N>", "<V>"), takeover=TAKEOVER_SENTENCE))


def add_unattended_commands(sub, common):
    """argparse wiring for watchdog, join-line, start-lead, lead-task-prompt, handoff, intent, reconcile and budget."""
    def leaf(name, fn, help):
        s = sub.add_parser(name, parents=[common], help=help, description=help)
        s.set_defaults(fn=state_command(fn))
        return s

    s = leaf("watchdog", cmd_watchdog, "the watchdog task, as role watchdog: buzz and post LEAD-SILENT when no "
                                       "step or pr change, mission branch push or mission PR merge happened for "
                                       "DURATION, or when no lead joined for DURATION after Matthew's decision to a "
                                       "parked lead; a reminder every 4 x DURATION while it lasts, and while a "
                                       "parked lead's request waits on Matthew; after a stall's alarm, at most one "
                                       "lead start for it through the lead task; never writes state")
    s.add_argument("room", type=int)
    s.add_argument("--silent-after", type=duration_arg, default=3 * 3600, metavar="DURATION",
                   help="like 3h or 45m (default 3h; drills use a short one)")
    s = leaf("join-line", cmd_join_line, "print the line that starts a lead")
    s.add_argument("room", type=int)
    s.add_argument("--takeover", action="store_true",
                   help="for a lead Matthew starts once the architect finds the old lead gone: take the lease "
                        "with lease take --takeover")
    s = leaf("start-lead", cmd_start_lead, "start a lead through the lead task's API trigger, with the join line as "
                                           "its text, and post LEAD-STARTED as ROLE (exit 1 transient: run it once "
                                           "more; 3 refused; 6 not configured or token rejected)")
    s.add_argument("room", type=int)
    s.add_argument("role", choices=START_ROLES)
    s.add_argument("--takeover", action="store_true",
                   help="the takeover join line, for a lead that stopped without handing over; needed while the "
                        "lease is held")
    s.add_argument("--force", action="store_true",
                   help="start even though a LEAD-STARTED under 30 minutes old has no LEAD ONLINE after it; also take "
                        "over a paused or stopped build whose lease is still held, only on Matthew's word to resume")
    s.add_argument("--seen", type=seen_arg, metavar="ID",
                   help="the room's newest comment ID when the start was decided (the architect's starter tasks), or "
                        "0 for a room with no comments: refuse (exit 3) if a lead message, or a LEAD-STARTED from "
                        "anyone, came after it")
    s.add_argument("--replacing", type=session_arg, metavar="SESSION",
                   help="with --takeover: the session that held the lease when the takeover was decided (the "
                        "architect's takeover starters); refuse (exit 3) unless it still holds it")
    leaf("lead-task-prompt", cmd_lead_task_prompt, "print the prompt of this repo's lead task, for Matthew to "
                                                   "paste when he creates the task")
    s = leaf("handoff", cmd_handoff, "record step, cursor and intent=none holding the lease, post HANDOFF, then "
                                     "release the lease; prints how to start the successor, and the join line")
    s.add_argument("room", type=int)
    s.add_argument("--step", required=True, help="the step the successor starts at")
    s.add_argument("--cursor", required=True, type=from_arg, metavar="ID",
                   help="the last comment this lead acted on (from a [cursor: ID] line it handled), or none")
    s = leaf("intent", cmd_intent, "record the intended outside action before taking it (needs the lease); a post "
                                   "intent also records the room's last comment ID")
    s.add_argument("room", type=int)
    s.add_argument("intent", help='e.g. "post ESCALATION-3", "merge PR #12 at <sha>", "open PR mission/M2-x", '
                                  '"close room", or none')
    s = leaf("reconcile", cmd_reconcile, "for a joining lead: the recorded state next to GitHub's facts, and a "
                                         "hint on the recorded intent; changes nothing")
    s.add_argument("room", type=int)
    leaf("budget", cmd_budget, "the mission's elapsed time against its phase's budget (exit 0 under, 6 over, "
                               "1 without mission_started)")


# --- end of unattended operation


def session_arg(s):
    if not re.fullmatch(SESSION_RE, s):
        raise argparse.ArgumentTypeError("a session ID: up to 64 letters, digits, '.', '_' or '-'")
    return s


def seen_arg(s):
    if not s.isdigit():
        raise argparse.ArgumentTypeError("takes a comment ID, or 0 for a room with no comments")
    return int(s)


def from_arg(s):
    if s != "none" and not s.isdigit():
        raise argparse.ArgumentTypeError("takes a comment ID, or none for the room's start")
    return s


def main():
    global REPO, TRUST, SESSION_OPT
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", type=repo_arg, help="OWNER/NAME (default: $ROOM_REPO, else this checkout's origin)")
    common.add_argument("--session", help="this participant's session ID (default: $ROOM_SESSION, "
                                          "else $CLAUDE_CODE_SESSION_ID's first 8 characters, else the hostname)")
    p = argparse.ArgumentParser(description="Agent room on a GitHub issue.",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def cmd(name, fn):
        s = sub.add_parser(name, parents=[common])
        s.set_defaults(fn=fn)
        return s

    cmd("new", cmd_new).add_argument("title")
    cmd("rooms", cmd_rooms)
    s = cmd("say", cmd_say); s.add_argument("room", type=int); s.add_argument("role", type=role_arg)
    s.add_argument("text", nargs="?")
    add_buzz_flags(s)
    s = cmd("read", cmd_read); s.add_argument("room", type=int); s.add_argument("role", type=role_arg, nargs="?")
    s.add_argument("--all", action="store_true")
    s.add_argument("--from", dest="from_id", type=from_arg, metavar="ID",
                   help="set the cursor to comment ID first (none: the room's start)")
    s = cmd("wait", cmd_wait); s.add_argument("room", type=int); s.add_argument("role", type=role_arg)
    s.add_argument("--timeout", type=int, default=540, help="seconds (default 540: a foreground wait stays under the 10-minute command limit)")
    s.add_argument("--interval", type=float, default=5, help="seconds between polls (default 5)")
    s = cmd("cursor", cmd_cursor); s.add_argument("room", type=int); s.add_argument("role", type=role_arg)
    s = cmd("close", cmd_close); s.add_argument("room", type=int); s.add_argument("role", type=role_arg)
    s.add_argument("text", nargs="?")
    add_buzz_flags(s)
    sub.add_parser("ping").set_defaults(fn=cmd_ping, repo=None)
    add_state_commands(sub, common)  # M2-B: state, lease, preflight
    add_gate_commands(sub, common)   # M3: gate, merge
    add_unattended_commands(sub, common)  # M4: watchdog, join-line, handoff, reconcile, budget; M6b: start-lead

    a = p.parse_args()
    SESSION_OPT = getattr(a, "session", None)
    if a.fn is cmd_ping:
        sys.exit(cmd_ping(a) or 0)
    REPO = a.repo or os.environ.get("ROOM_REPO") or repo_from_checkout()
    if not REPO:
        sys.exit("which repo? Run inside the project's checkout, or pass --repo OWNER/NAME")
    try:
        # v1: ROOM_TRUST adds logins to the gh login; it never replaces it
        env_trust = os.environ.get("ROOM_TRUST", "")
        TRUST = default_trust() | {s.strip().lower() for s in env_trust.split(",") if s.strip()}
        sys.exit(a.fn(a) or 0)
    except GhError as e:
        sys.exit(f"github error: {e}")


if __name__ == "__main__":
    main()
