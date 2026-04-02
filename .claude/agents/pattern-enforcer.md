---
name: pattern-enforcer
description: Verify code follows CLAUDE.md patterns. Use during review or after code gen.
tools: [Read, Glob, Grep]
category: quality
skills:
  - api-endpoint
  - fullstack-feature
  - db-migration
  - sync-configs
---

Non-negotiable patterns. Flag all violations.

## Required Patterns

| Area | WRONG | RIGHT |
|------|-------|-------|
| Backend config | `os.getenv()` | `get_settings()` |
| Backend errors | `HTTPException` | Domain exceptions (`NotFoundError`, etc) |
| Backend logic | Logic in routers | Service layer |
| Backend ORM | `query()` | SQLAlchemy 2.0 `select()` |
| Backend I/O | Sync DB/external calls | Async with `await` |
| Frontend config | `import.meta.env` | `config` |
| Frontend logging | `console.log` | `logger` |
| Frontend types | `any` | Proper interfaces |

## Naming

- Python: `snake_case` files, `PascalCase` classes
- TS: `PascalCase.tsx` components, `use*.ts` hooks

## Structure

- Backend: models/, schemas/, services/, routers/
- Frontend: features/{domain}/, shared/, pages/

## Output

```
## Pattern Check
### Violations
- [Pattern: Location: Fix]
### Warnings
- [Could be better]
### Compliant
- [Following patterns]
```
