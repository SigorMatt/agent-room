# Manuals: I want to…

Short how-tos for running agent-room from your phone. Each page says when to use it, what you need first, the steps with the exact lines to paste, what you should see, and what to do if you don't.

You use three apps: the Claude app (the architect chat in the project's Claude Project, and the Code tab where leads run), GitHub, and ntfy. A few setup pages need a computer browser instead. You never run `room.py` yourself: you paste lines into the architect chat or a lead session, or change a setting.

A page that left you with a question is a bug: [report it](report-a-pipeline-problem.md).

## One-time setup

- I want to make agent-room public → [Make agent-room public](make-agent-room-public.md)
- I want to save the skill in each Claude account → [Save the skill, in each account](save-the-skill.md)
- I want to connect GitHub to Claude → [Connect GitHub](connect-github.md)
- I want to get buzzes on my phone → [Install ntfy and subscribe](install-ntfy-and-subscribe.md)
- I want to create the cloud environment for leads → [Create the `agent-room` cloud environment](create-the-cloud-environment.md)
- I want to check that buzzes reach my phone → [Test the buzz](test-the-buzz.md)

## Starting a project

- I want to create the project's repo → [Create the repo](create-the-repo.md)
- I want to give the architect a Claude Project → [Create the project's Claude Project](create-the-claude-project.md)
- I want to start a project from nothing → [Start from scratch](start-from-scratch.md)
- I want to start from an earlier chat → [Start from a discussion](start-from-a-discussion.md)
- I want to start from an earlier chat and existing code → [Start from a discussion plus code](start-from-a-discussion-plus-code.md)
- I want to check and approve the plan → [Approve the playbook](approve-the-playbook.md)
- I want to add the websites and secrets a project needs → [Set up environment needs](set-up-environment-needs.md)
- I want to fix a failed preflight check → [Fix preflight](fix-preflight.md)
- I want leads to start each other without me → [Set up the lead task](set-up-the-lead-task.md)
- I want to start building a phase → [Kick off a phase and start its first lead](kick-off-a-phase.md)

## During a run

- I want to answer a buzz (`ESCALATION`, `MERGE-HOLD`, `NEXT-LEAD-NEEDED`, `PAUSED`, `STOPPED`, `DONE`, `LEAD-SILENT`) → [Answer a buzz](answer-a-buzz.md)
- I want to see the design or where the build stands → [Read the design and state on the state branch](read-the-state-branch.md)
- I want to pause or stop the build from GitHub → [Steer from GitHub](steer-from-github.md)
- I want to change the design while it builds → [Change something mid-build](change-something-mid-build.md)
- I want to halt the build, or let it rest → [STOP or PAUSE](stop-or-pause.md)
- I want to start a lead myself → [Start the next lead by hand](start-the-next-lead-by-hand.md)
- I want to end a design session → [Wrap up an architect session](wrap-up-an-architect-session.md)

## Maintenance

- I want to move a project to a newer agent-room release → [Upgrade a project](upgrade-a-project.md)
- I want to build more after `DONE` → [Start a new phase](start-a-new-phase.md)
- I want to judge Qodo, or switch it off → [Judge Qodo and switch it off](judge-qodo-and-switch-it-off.md)
- I want to fix buzzes that fail → [Handle ntfy limit errors](handle-ntfy-limit-errors.md)
- I want to run a project on my other Claude account → [Move a project to the other account](move-a-project-to-the-other-account.md)
- I want to report a problem with agent-room or a manual → [Report a pipeline problem](report-a-pipeline-problem.md)

## Reference

- I want to fix something that looks wrong → [Troubleshooting](troubleshooting.md)
- I want to know what a room message means → [Message kinds](message-kinds.md)
- I want to know where a file lives and who changes it → [Files and owners](files-and-owners.md)
- I want to know why a pull request was held → [Merge-hold list](merge-hold-list.md)
- I want to look up a word → [Glossary](glossary.md)
