---
name: docs
description: Generate or update docs for recent code changes using the docs-generator agent. Use after APIs, components, hooks, services, or workflows change.
---

# Generate Docs

Use this after code changes that should leave behind user-facing or maintainer-facing documentation.
Prefer documenting only the changed surface area instead of broad repo rewrites.

## What to Document

- New API endpoints -> OpenAPI/docstrings
- New components -> Props interface + usage example
- New hooks -> JSDoc with parameters + return type
- New services -> Method signatures + examples
- Architecture changes -> Update relevant CLAUDE.md

## Steps

1. Identify changes: `git diff HEAD~5 --name-only`
2. Spawn `docs-generator` agent with file list
3. Review generated docs
4. Commit separately: `git commit -m "docs: document X feature"`
