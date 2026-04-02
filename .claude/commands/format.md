---
description: Format changed or specified JS/TS and Python files with the repo formatters
---

# Format Files

Use this after edits and before broader verification so style noise does not pollute later review.
Format only the files that changed unless the user asked for a larger formatting sweep.

Run formatters on changed or specified files.

```bash
# All changed files
.agents/skills/format/scripts/auto-format.sh

# Specific files
.agents/skills/format/scripts/auto-format.sh path/to/file.ts path/to/file.py
```

## Formatters

- **TypeScript/JavaScript** (`.ts`, `.tsx`, `.js`, `.jsx`): `npx prettier --write`
- **Python** (`.py`): `ruff format`

Use after editing source files, before committing, or when style is inconsistent.
