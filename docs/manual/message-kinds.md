# Message kinds

[All manuals](README.md)

## When to use it

To look up a message in the room: who sent it, whether it buzzes, and what you do.

## What you need first

- The room, or the buzz's title. Each message starts with its kind.

## Steps

1. Find the kind. `n` is a number shared by escalations and holds in one room, so `DECISION-n` answers exactly one of them.

   | Kind | From | Buzzes | Means | You |
   | --- | --- | --- | --- | --- |
   | `PLAN` | Lead | No | The phase's missions, as planned or re-planned | Nothing |
   | `LEAD ONLINE` | Lead | No | A new lead has taken over | Nothing |
   | `STATUS` | Lead | No | A task or step finished, or a note | Nothing |
   | `ESCALATION-n` | Lead | Yes | It needs your decision | [Answer a buzz](answer-a-buzz.md) |
   | `MERGE-HOLD-n` | Lead | Yes | A pull request is held, with a reason | [Answer a buzz](answer-a-buzz.md) |
   | `HANDOFF` | Lead | No | This lead's turn ends; it starts the next one | Nothing |
   | `LEAD-STARTED` | Lead, architect or watchdog | No | A new lead was started through the lead task, with a link to its session, the kind of join line and who started it. `started by watchdog after DECISION-n` is the lead for your decision, not a takeover. `LEAD-STARTED: unconfirmed (…)` means the start may have worked: nobody starts another for 30 minutes. Its `LEAD ONLINE` should follow within about 15 minutes | Nothing |
   | `NEXT-LEAD-NEEDED` | Lead | Yes | The next lead couldn't be started; the message says why | [Answer a buzz](answer-a-buzz.md) |
   | `PAUSED` | Lead | Yes | Paused at a safe point; the lead ended | Resume when you like ([Start the next lead by hand](start-the-next-lead-by-hand.md)) |
   | `STOPPED` | Lead | Yes | Halted on `STOP`; the lead ended | [Answer a buzz](answer-a-buzz.md) |
   | `DONE` | Lead | Yes | The phase is complete and the room closed | [Answer a buzz](answer-a-buzz.md) |
   | `LEAD-SILENT` | Watchdog | Yes | No progress for three hours. With the lead task set up, a takeover lead is started too, at most twice for the same stall. The last one, "two takeover leads made no progress; no more starts", starts nothing | [Answer a buzz](answer-a-buzz.md) |
   | `ACK DECISION-n`, `ACK CHANGE-n` | Lead | No | Received and applied | Nothing |
   | `DECISION-n` | Architect | No | Your answer to escalation or hold n, with how the mission continues | Wait for the ACK |
   | `CHANGE-n` | Architect | No | A design change in the middle of a phase | [Change something mid-build](change-something-mid-build.md) |
   | `PAUSE` | Architect or you | No | Finish running work, save, end | [STOP or PAUSE](stop-or-pause.md) |
   | `STOP` | Architect or you | No | Halt now | [STOP or PAUSE](stop-or-pause.md) |

2. Each message also names its sender's role and session. A comment you post from GitHub shows as `human (SigorMatt)` and outranks both agents.

## What you should see

- Every message starts with one of these kinds. A buzz's title is the kind, the project and the room number, never the content.

## If you don't

- A message without a known kind came from someone other than you: agents ignore comments from other logins.
- A buzzing kind arrived without a buzz: [Handle ntfy limit errors](handle-ntfy-limit-errors.md).
