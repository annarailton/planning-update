---
name: clean-slop
description: Audit recent changes with the 5 quality agents, fix findings, and re-verify. Use before final review or when code quality is uncertain.
---

# Clean Slop

Use this after implementation when you want a quality sweep, not as a replacement for normal tests.
The goal is to collect findings, fix them, and re-verify in one pass.

## 1. Gather context

```bash
git diff HEAD~5 --name-only
git diff HEAD~5
```

## 2. Audit (parallel subagents)

Single message, 5 agent calls:

| Agent                | Focus                              |
| -------------------- | ---------------------------------- |
| code-reviewer        | Quality, patterns, types, dead code, component-vs-hook side-effect boundaries |
| pattern-enforcer     | AGENTS.md compliance (including "useEffect in custom hooks, not page/feature components") |
| security-auditor     | OWASP, auth, secrets, injection    |
| edge-case-auditor    | Error handling, nulls, boundaries  |
| performance-analyzer | N+1, memory leaks, bottlenecks     |

Each agent gets: file list, full diff, instruction to report ALL issues (critical/high/medium/low), and explicit instruction to flag `useEffect` in page/feature components when the logic should be moved to custom hooks.

## 3. Fix ALL issues

Spawn parallel implementor agents grouped by file to fix every reported issue — all severities, not just critical/high. No file conflicts: one agent per file group.

## 4. Verify

Re-run affected audit agents to confirm zero remaining issues.

## 5. Summary table

| Agent                | Before | After | Status |
| -------------------- | ------ | ----- | ------ |
| code-reviewer        | ...    | ...   | ...    |
| pattern-enforcer     | ...    | ...   | ...    |
| security-auditor     | ...    | ...   | ...    |
| edge-case-auditor    | ...    | ...   | ...    |
| performance-analyzer | ...    | ...   | ...    |
