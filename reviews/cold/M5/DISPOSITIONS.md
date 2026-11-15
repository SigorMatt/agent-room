# Cold dispositions, M5

| ID | severity | file | finding | disposition | evidence |
| --- | --- | --- | --- | --- | --- |
| R1-1 | high | LEAD.md | A resumed lead handles an old PAUSE or STOP again | fixed in ddbe111 | Cursor recorded before PAUSED/STOPPED and on each DECISION/CHANGE; manuals in c1f7c43; docs checked by tests/test_docs.py |
| R1-2 | high | LEAD.md | The stop-after-merge drill ends every later lead too | fixed in 6119d76 | Fires only after the session's own merge; the architect removes the line (4a464d6); docs checked by tests/test_docs.py |
| R1-3 | medium | LEAD.md | A new phase reads from the old room's cursor | fixed in c410f21 | A new phase reads from none and resets the cursor; docs checked by tests/test_docs.py |
| R1-4 | medium | LEAD.md | Phase end deletes the watchdog before DONE | fixed in a9493ee | DONE and close first, then delete, then release; step done finishes section 7; manuals in 902b5b4; docs checked by tests/test_docs.py |
| R1-5 | medium | LEAD.md | The watchdog to delete is found by prompt text | fixed in a9493ee | By the task ID on PLAYBOOK.md's watchdog: line; docs checked by tests/test_docs.py |
| R1-6 | medium | LEAD.md | A clean scoped review always routes to PR | fixed in b31f0e1 | Records its return step; returns there (aebfadf); docs checked by tests/test_docs.py |
| R1-7 | medium | LEAD.md | No way to extend an overrun budget | fixed in 244aadb | Back to Build or granted time restarts the clock; escalate once; DECISION format has a Time line (6290011); docs checked by tests/test_docs.py |
| R1-8 | medium | LEAD.md | A DECISION rewrites only pending-escalation rows | fixed in 39279fc | Rewrites every row it covers; docs checked by tests/test_docs.py |
| R1-9 | medium | LEAD.md | The gate's naming rule for escalations isn't documented | fixed in 39279fc | Escalations and holds name findings by cold ID, full Qodo title or dispositions path; docs checked by tests/test_docs.py |
| R1-10 | medium | LEAD.md | A lead at step spec skips the in-progress mission | fixed in f66da72 | Resumes the in-progress mission first; docs checked by tests/test_docs.py |
| R1-11 | medium | LEAD.md | Review templates not downloaded; Qodo machine-line placement | fixed in e8d02c6 | Setup downloads templates/reviews; machine lines above the table; docs checked by tests/test_docs.py |
| R1-12 | medium | LEAD.md | Join acts on hints before reading the room | fixed in c410f21 | Reads the room right after the lease, handles STOP/PAUSE/DECISION first; docs checked by tests/test_docs.py |
| R1-13 | medium | ARCHITECT.md | Takeover given before a live lead can answer LEAD-SILENT | fixed in 3d78e06 | Waits for the next check-in (~35 min); room.py wording in d90c84f; docs checked by tests/test_docs.py |
| R1-14 | medium | ARCHITECT.md | No path for a lead that dies while waiting for the owner | fixed in 3d78e06 | No answer to check the room within ~35 min gets a takeover; docs checked by tests/test_docs.py |
| R1-15 | low | LEAD.md | Several hold reasons have no form | fixed in 39279fc | Written reason 1, reason 5; docs checked by tests/test_docs.py |
| R1-16 | low | LEAD.md | Final-check findings decided without a push | fixed in 4fd3e10 | Fetch and rows committed and pushed as records; docs checked by tests/test_docs.py |
| R1-17 | low | LEAD.md | A gate failure the records can't fix has no step | fixed in 570bd86 | Pipeline fault: escalate and wait (aebfadf); docs checked by tests/test_docs.py |
| R1-18 | low | LEAD.md | Successor task approval setting not checked | fixed in 7a47854 | Checked; NEXT-LEAD-NEEDED if runs would ask; docs checked by tests/test_docs.py |
| R1-19 | low | LEAD.md | Qodo off/no-review paths don't record step gate | fixed in 1326dd1 | Record step gate; docs checked by tests/test_docs.py |
| R1-20 | low | briefs/auditor.md | Auditor rejects the reader's cold caught form | fixed in 3ee7f36 | Accepts yes (<ID>); docs checked by tests/test_docs.py |
| R1-21 | low | briefs/planner.md | Planner runs tests in the lead's checkout | fixed in 89a3982 | Uses its own fresh clone; docs checked by tests/test_docs.py |
| R1-22 | low | ARCHITECT.md | A state-unreadable alarm is treated as a dead lead | fixed in 3d78e06 | Restore the state branch first (c570229); docs checked by tests/test_docs.py |
