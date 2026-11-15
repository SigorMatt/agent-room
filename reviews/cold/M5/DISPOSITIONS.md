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
| R2-1 | high | LEAD.md | Back to Build after the PR exists has no path | fixed in 228f343 | Keeps the PR; granted extra cold rounds (round 3 on) and Qodo rounds on the same PR; cold brief round-2-and-later variant; docs checked by tests/test_docs.py |
| R2-2 | medium | ARCHITECT.md | Merge as is offered for failing checks (reason 3) | fixed in 5f2ef19 | Reason 3 offers back to Build, fix or relax the check, or drop; docs checked by tests/test_docs.py |
| R2-3 | medium | LEAD.md | The QODO-VALUE draft is lost at a takeover | fixed in d31f352 | Draft line committed on the state branch, finalised at close; docs checked by tests/test_docs.py |
| R2-4 | medium | ARCHITECT.md | A pipeline fault can't reach the stuck lead | fixed in 6f8ac2a | Patched release, pin bump, DECISION to re-download; LEAD.md re-downloads (f75c4c8); docs checked by tests/test_docs.py |
| R2-5 | medium | ARCHITECT.md | A foreground-builder lead can't check in before a takeover; pushes skip the lease | fixed in 10c3a04 | Recent push or STATUS earns one more check-in; LEAD.md lease check before every push, STATUS before each foreground builder (35760f3); docs checked by tests/test_docs.py |
| R2-6 | medium | LEAD.md | Merge as is after a long hold still escalates the budget | fixed in 4ab2860 | Budget only during Build and rounds; merge as is restarts the clock; ARCHITECT.md in 6f8ac2a; docs checked by tests/test_docs.py |
| R2-7 | medium | LEAD.md | Weakened tests aren't a lead-judged hold (B-4) | fixed in b1882e3 | Gate step holds a cold finding of weakened tests under reason 5 naming the files; hold list in 6e8d573; docs checked by tests/test_docs.py |
| R2-8 | low | LEAD.md | A joining lead handles a DECISION off the mission branch | fixed in c45150d | Switches to the mission branch first; docs checked by tests/test_docs.py |
| R2-9 | low | ARCHITECT.md | state init restore restarts the lead records | fixed in 88bbbfd | Re-push from any copy first; state init last, with a DECISION to rebuild records and the counter; docs checked by tests/test_docs.py |
| R2-10 | low | LEAD.md | Close repeats its line and STATUS | fixed in d31f352 | Close does only what is missing; docs checked by tests/test_docs.py |
| R2-11 | low | LEAD.md | Phase end can't tell whether the room was closed | fixed in 6be51a3 | Checks the issue state; docs checked by tests/test_docs.py |
| R2-12 | low | LEAD.md | A successor task that asks stays armed | fixed in 2963109 | Disabled, never deleted, before NEXT-LEAD-NEEDED; docs checked by tests/test_docs.py |
| R2-13 | low | LEAD.md | A dropped mission is resumed | fixed in ca1d99e | Row marked dropped, PR closed, never resumed; docs checked by tests/test_docs.py |
| R2-14 | low | LEAD.md | A lead joining at gate misses reason 6 | fixed in b1882e3 | The gate step checks reason 6 from the two PRs' dispositions; docs checked by tests/test_docs.py |
