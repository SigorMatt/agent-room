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
   | `STATUS` | Lead | Usually not | A task or step finished, or a note. When a `STATUS` does buzz, it's a real request: the lead's `ESCALATION` or `MERGE-HOLD` buzz failed, and a decision is needed | Usually nothing. A `STATUS` buzz: open the room and [answer a buzz](answer-a-buzz.md) |
   | `ESCALATION-n` | Lead | Yes | It needs your decision | [Answer a buzz](answer-a-buzz.md) |
   | `MERGE-HOLD-n` | Lead | Yes | A pull request is held, with a reason | [Answer a buzz](answer-a-buzz.md) |
   | `HANDOFF` | Lead | No | This lead's turn ends; it starts the next one | Nothing |
   | `LEAD-STARTED` | Lead, architect or watchdog | No | A new lead was started through the lead task, with a link to its session, the kind of join line and who started it. `LEAD-STARTED: by hand …` means you start it with the line the architect gives you. `started by watchdog`: the watchdog's one start for a stall, after its alarm. `LEAD-STARTED: unconfirmed (…)` means the start may have worked: nobody starts another for 30 minutes. Its `LEAD ONLINE` should follow within about 15 minutes | Nothing |
   | `NEXT-LEAD-NEEDED` | Lead | Yes | The next lead couldn't be started; the message says why | [Answer a buzz](answer-a-buzz.md) |
   | `PAUSED` | Lead | Yes | Paused at a safe point; the lead ended | Resume when you like ([Start the next lead by hand](start-the-next-lead-by-hand.md)) |
   | `STOPPED` | Lead | Yes | Halted on `STOP`; the lead ended | [Answer a buzz](answer-a-buzz.md) |
   | `DONE` | Lead | Yes | The phase is complete and the room closed | [Answer a buzz](answer-a-buzz.md) |
   | `LEAD-SILENT` | Watchdog | Yes | No progress for three hours. "no lead joined after DECISION-n": no lead joined in the three hours after your decision. "no lead has joined room N in 12h": the phase's first lead never joined. "still no progress since …", "still no lead joined after DECISION-n …", "still state unreadable (…)" or "still no lead has joined room N": a reminder every 12 hours while it lasts. "still waiting for Matthew: <KIND>-n since …": the oldest `ESCALATION` or `MERGE-HOLD` you haven't answered has waited 12 hours for your decision. Once a lead has joined, the watchdog may start one lead itself in the run of a stall's first alarm, never later, but only for a lead that never came (no lead posted or took the lease since the stall began); the architect decides the rest | [Answer a buzz](answer-a-buzz.md) |
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
