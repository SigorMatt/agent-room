#!/usr/bin/env python3
"""Stand-in for `gh api` for the repo reads preflight needs; every other call goes to fake_gh.py.

FAKE_GH_STATE names a JSON file with the answers. Each value is a response body, or
{"_status": N, "message": "..."} for an error:
  repo        GET repos/O/N                         (default: push access, delete_branch_on_merge on)
  protection  GET repos/O/N/branches/main/protection (default: 404 Branch not protected)
  rules       GET repos/O/N/rules/branches/main      (default: [])
  rulesets    {"<id>": body} for GET repos/O/N/rulesets/<id>
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
method = args[args.index("-X") + 1] if "-X" in args else "GET"
path = next(x for x in args[1:] if not x.startswith("-") and x not in ("api", method))
parts = path.split("?")[0].split("/")

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


if method == "GET" and parts[0] == "repos" and len(parts) >= 3:
    rest = parts[3:]
    if rest == []:
        respond(cfg.get("repo", {"full_name": f"{parts[1]}/{parts[2]}", "permissions": {"push": True, "admin": True},
                                 "delete_branch_on_merge": True}))
    if rest == ["branches", "main", "protection"]:
        respond(cfg.get("protection", {"_status": 404, "message": "Branch not protected"}))
    if rest == ["rules", "branches", "main"]:
        respond(cfg.get("rules", []))
    if len(rest) == 2 and rest[0] == "rulesets":
        respond(cfg.get("rulesets", {}).get(rest[1], {"_status": 404, "message": "Not Found"}))

os.execv(sys.executable, [sys.executable, os.path.join(HERE, "fake_gh.py"), *args])
