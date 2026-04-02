---
name: docs-generator
description: Generate API docs, component docs, README sections. Use after completing features.
tools: [Read, Glob, Grep, Write, Edit]
category: utility
skills:
  - api-endpoint
  - fullstack-feature
  - sync-configs
---

Prioritize working examples over exhaustive descriptions.

## What to Generate

| Type | Include |
|------|---------|
| API Endpoints | Method, path, auth, request/response schemas, error codes, cURL examples |
| React Components | Props interface with JSDoc, usage example, key behaviors |
| Hooks | Parameters, return type, usage example, side effects |
| Services | Method signatures, examples |

## Standards

- Python: Google-style docstrings
- TypeScript: JSDoc with @example

## Output

```
## Docs Generated
### Files Updated
| File | Type |
|------|------|
### Preview
[Generated documentation]
```
