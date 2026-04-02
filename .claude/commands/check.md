---
description: Run lint, type checks, and tests across backend and frontend
---

# Check All

Use this when you need repo-level verification, especially before calling work done.
Default to the full check sequence unless the user asked for a narrower failing check only.

Run all validation:

```bash
pnpm lint:backend && pnpm lint:frontend && pnpm test:backend && pnpm test:frontend
```

Or: `pnpm check:all`

On failure: fix issues, re-run failed check, continue to next.
