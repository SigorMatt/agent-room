#!/usr/bin/env python3
"""Stand-in for `gh api` for the repo reads preflight and the gate need; every other call goes to fake_gh.py.

FAKE_GH_STATE names a JSON file with the answers. Each value is a response body, or
{"_status": N, "message": "..."} for an error:
  repo        GET repos/O/N                         (default: push access, delete_branch_on_merge and
                                                     allow_merge_commit on)
  protection  GET repos/O/N/branches/main/protection (default: 404 Branch not protected)
  rules       GET repos/O/N/rules/branches/main      (default: [])
  rulesets    {"<id>": body} for GET repos/O/N/rulesets/<id>
  pulls       {"<n>": PR object} for GET repos/O/N/pulls/<n> (default: 404), and the list
              GET repos/O/N/pulls?state=open|closed|all[&head=OWNER:ref]
  commits     {"<sha>": commit object} for GET repos/O/N/commits/<sha>. Default: with FAKE_GH_GIT_ROOT set,
              the committer date of <sha> in the bare repo $FAKE_GH_GIT_ROOT/O/N.git, else 404
  check_runs  {"<sha>": [check run]} for GET repos/O/N/commits/<sha>/check-runs (default: none)
  statuses    {"<sha>": [status]} for GET repos/O/N/commits/<sha>/status (default: none)
  merge       the answer to PUT repos/O/N/pulls/<n>/merge. Default: 200 with a merge sha when the
              body's sha is the PR's head sha, else 409 as GitHub answers a moved head
Every merge call is appended, as a JSON line, to FAKE_GH_STATE + ".calls".
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from urllib.parse import parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
method = args[args.index("-X") + 1] if "-X" in args else "GET"
path = next(x for x in args[1:] if not x.startswith("-") and x not in ("api", method))
parts = path.split("?")[0].split("/")
query = {k: v[0] for k, v in parse_qs(path.partition("?")[2]).items()}

try:
    with open(os.environ["FAKE_GH_STATE"]) as f:
        cfg = json.load(f)
except (KeyError, FileNotFoundError):
    cfg = {}


def respond(obj):
    if isinstance(obj, dict) and "_status" in obj:
        print(json.dumps({"message": obj["message"]}))
        print(f"gh: {obj['message']} (HTTP {obj['_status']})", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(obj))
    sys.exit(0)


def page(items):
    per, n = int(query.get("per_page", 30)), int(query.get("page", 1))
    return items[(n - 1) * per: n * per]


if method == "GET" and parts[0] == "repos" and len(parts) >= 3:
    rest = parts[3:]
    if rest == []:
        respond(cfg.get("repo", {"full_name": f"{parts[1]}/{parts[2]}", "permissions": {"push": True, "admin": True},
                                 "delete_branch_on_merge": True, "allow_merge_commit": True}))
    if rest == ["branches", "main", "protection"]:
        respond(cfg.get("protection", {"_status": 404, "message": "Branch not protected"}))
    if rest == ["rules", "branches", "main"]:
        respond(cfg.get("rules", []))
    if len(rest) == 2 and rest[0] == "rulesets":
        respond(cfg.get("rulesets", {}).get(rest[1], {"_status": 404, "message": "Not Found"}))
    if len(rest) == 2 and rest[0] == "pulls":
        respond(cfg.get("pulls", {}).get(rest[1], {"_status": 404, "message": "Not Found"}))
    if rest == ["pulls"]:
        want, head = query.get("state", "open"), query.get("head")

        def head_of(p):  # OWNER:ref, as GitHub's head filter reads it
            h = p.get("head") or {}
            return f"{((h.get('repo') or {}).get('full_name') or '').split('/')[0]}:{h.get('ref')}"
        respond(page([p for p in cfg.get("pulls", {}).values()
                      if (want == "all" or p.get("state") == want) and (head is None or head_of(p) == head)]))
    if len(rest) == 2 and rest[0] == "commits":
        if rest[1] in cfg.get("commits", {}):
            respond(cfg["commits"][rest[1]])
        root = os.environ.get("FAKE_GH_GIT_ROOT")
        r = subprocess.run(["git", "--git-dir", os.path.join(root, parts[1], parts[2] + ".git"), "show", "-s",
                            "--format=%ct", rest[1]], capture_output=True, text=True) if root else None
        if r is None or r.returncode != 0:
            respond({"_status": 404, "message": "No commit found for SHA: " + rest[1]})
        date = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(r.stdout.strip())))
        respond({"sha": rest[1], "commit": {"committer": {"date": date}}})
    if len(rest) == 3 and rest[0] == "commits" and rest[2] == "check-runs":
        runs = cfg.get("check_runs", {}).get(rest[1], [])
        respond({"total_count": len(runs), "check_runs": page(runs)})
    if len(rest) == 3 and rest[0] == "commits" and rest[2] == "status":
        statuses = cfg.get("statuses", {}).get(rest[1], [])
        states = {s.get("state") for s in statuses}
        combined = "failure" if states & {"failure", "error"} else "pending" if states - {"success"} or not states \
            else "success"
        respond({"state": combined, "total_count": len(statuses), "statuses": page(statuses)})

if method == "PUT" and parts[0] == "repos" and len(parts) == 6 and parts[3] == "pulls" and parts[5] == "merge":
    body = json.loads(sys.stdin.read()) if "--input" in args else {}
    with open(os.environ["FAKE_GH_STATE"] + ".calls", "a") as f:
        f.write(json.dumps({"pr": parts[4], **body}) + "\n")
    if "merge" in cfg:
        respond(cfg["merge"])
    head = ((cfg.get("pulls", {}).get(parts[4]) or {}).get("head") or {}).get("sha")
    if body.get("sha") != head:
        respond({"_status": 409, "message": "Head branch was modified. Review and try the merge again."})
    respond({"sha": hashlib.sha1(f"merge {parts[4]} {head}".encode()).hexdigest(), "merged": True,
             "message": "Pull Request successfully merged"})

os.execv(sys.executable, [sys.executable, os.path.join(HERE, "fake_gh.py"), *args])
