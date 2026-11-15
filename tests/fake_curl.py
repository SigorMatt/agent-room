#!/usr/bin/env python3
"""Stand-in for curl.

A buzz (any URL but the fire endpoint) appends its arguments to FAKE_CURL_LOG and fails if FAKE_CURL_FAIL is set.

A POST to a lead task's fire endpoint (.../v1/claude_code/routines/<task>/fire) appends its arguments to
FAKE_FIRE_LOG (else FAKE_CURL_LOG) and answers as the API would:
  FAKE_FIRE_FAIL    curl fails as on a network error, printing this text (%TOKEN% becomes the bearer token)
  FAKE_FIRE_STATUS  the HTTP status (default 200)
  FAKE_FIRE_BODY    the body (default: a routine_fire answer naming a new session); %TOKEN% as above
It honours -w's %{http_code}, as room.py reads the status from it.
"""
import json
import os
import sys

args = sys.argv[1:]
url = next((x for i, x in enumerate(args) if x.startswith(("http://", "https://")) and
            (i == 0 or args[i - 1] not in ("-H", "-d", "--data-raw", "-w", "-o", "-m", "-X"))), "")

if "/v1/claude_code/routines/" not in url:
    with open(os.environ["FAKE_CURL_LOG"], "a") as f:
        f.write(json.dumps(args) + "\n")
    if os.environ.get("FAKE_CURL_FAIL"):
        print(f"curl: (22) The requested URL returned error: {os.environ['FAKE_CURL_FAIL']}", file=sys.stderr)
        sys.exit(22)
    sys.exit(0)

log = os.environ.get("FAKE_FIRE_LOG") or os.environ["FAKE_CURL_LOG"]
with open(log, "a") as f:
    f.write(json.dumps(args) + "\n")
headers = [args[i + 1] for i, x in enumerate(args[:-1]) if x == "-H"]
token = next((h.split("Bearer ", 1)[1] for h in headers if h.startswith("Authorization: Bearer ")), "")
if os.environ.get("FAKE_FIRE_FAIL"):
    print(f"curl: (7) {os.environ['FAKE_FIRE_FAIL'].replace('%TOKEN%', token)}", file=sys.stderr)
    sys.exit(7)
with open(log + ".count", "a+") as f:  # a new session for each start
    f.seek(0)
    n = len(f.read()) + 1
    f.write(".")
status = os.environ.get("FAKE_FIRE_STATUS", "200")
body = os.environ.get("FAKE_FIRE_BODY")
if body is None:
    sid = f"session_fake{n:04d}"
    body = json.dumps({"type": "routine_fire", "claude_code_session_id": sid,
                       "claude_code_session_url": f"https://claude.ai/code/{sid}"})
body = body.replace("%TOKEN%", token)
fmt = args[args.index("-w") + 1] if "-w" in args else ""
sys.stdout.write(body + fmt.replace("%{http_code}", status))
