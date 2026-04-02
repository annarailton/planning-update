---
name: status
description: Summarize current project status from the plan doc and git history without re-exploring the codebase. Use for status, progress, next steps, or "what's next" requests.
---

# Status Check

Use this for fast project-state answers.
Stay anchored to plan docs and git history; do not re-audit the entire codebase unless the user asks for a deeper review.

1. Read the current implementation plan (find it: `docs/implementation-plan*.md` or similar)
2. Run `git log --oneline -20` for recent commits
3. Identify: current phase, what's done, what remains
4. Report concisely:
   - Current phase + % complete
   - Last 3-5 commits (summarized)
   - Next action items
5. Do NOT re-explore the full codebase — use docs and git history only
6. If no plan doc exists, say so and ask user to specify current priorities
