# Playbook

pipeline: main
repo: OWNER/NAME
room: 0
test: <command>

Owned by the architect; the lead reads it and acts on it. Every item has testable acceptance criteria that a cloud machine can check (4 CPUs, 16 GB, no GPU, internet only through the allowlist). Anything else is marked as a manual check for Matthew.

## Phases

### Phase 1: <name>

Goal: <one sentence>. Items: P1-1. Mission budget: 8 hours.

## Items with criteria

### P1-1: <title>

- [ ] <criterion, with the check that proves it>
- [ ] <criterion> (manual check for Matthew)

## Merge-hold list

A PR touching any of these areas is held for Matthew (`MERGE-HOLD-n`). Edit the patterns per project: `*` stays within one path segment, `**/` matches any number of directories, including none.

- CI and workflow files: `.github/workflows/**`, `.github/actions/**`
- Authentication, cryptography or secrets handling: `**/auth/**`, `**/crypto/**`, `**/*secret*`
- New dependencies: `**/requirements*.txt`, `**/pyproject.toml`, `**/setup.py`, `**/setup.cfg`, `**/Pipfile`,
  `**/package.json`, `**/go.mod`, `**/Cargo.toml`
- Destructive data migrations: `**/migrations/**`
- Deleted or weakened tests: `**/tests/**`, `**/test/**`, `**/__tests__/**`, `**/*_test.*`, `**/*.test.*`, `**/test_*`

## Environment needs

- Domains to allow: none
- Secrets to add: none

## Lead's discretion

- <areas the lead decides without escalating, e.g. internal naming, test layout>

## Phase 0 known debt

None. For an existing codebase: what exists, the known debt, and a green `main` as the first criterion.
