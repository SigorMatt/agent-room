#!/usr/bin/env python3
"""Stand-in for curl: appends its arguments to FAKE_CURL_LOG and fails if FAKE_CURL_FAIL is set."""
import json
import os
import sys

with open(os.environ["FAKE_CURL_LOG"], "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
if os.environ.get("FAKE_CURL_FAIL"):
    print(f"curl: (22) The requested URL returned error: {os.environ['FAKE_CURL_FAIL']}", file=sys.stderr)
    sys.exit(22)
