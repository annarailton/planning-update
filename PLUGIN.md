# Fullstack Template - Claude Code Plugin

Custom Claude Code plugin for scaffolding and code quality in the Tomoro AI Fullstack Template.

> **New to the plugin?** See [PLUGIN-GUIDE.md](./PLUGIN-GUIDE.md) for workflows, best practices, and tips for getting the best results.

## Quick Reference

### Slash Commands

| Command                          | Description                                                    |
| -------------------------------- | -------------------------------------------------------------- |
| `/fullstack:feature-new <name>`  | Create complete E2E feature (backend + frontend)               |
| `/backend:feature-new <name>`    | Create backend feature (model, schema, service, router, tests) |
| `/backend:router-new <name>`     | Create FastAPI router with CRUD endpoints                      |
| `/backend:service-new <name>`    | Create service class with async methods                        |
| `/backend:schema-new <name>`     | Create Pydantic request/response schemas                       |
| `/backend:model-new <name>`      | Create SQLAlchemy model                                        |
| `/frontend:feature-new <name>`   | Create frontend feature (components, hooks, services, types)   |
| `/frontend:component-new <name>` | Create React component with props interface                    |
| `/frontend:hook-new <name>`      | Create custom hook                                             |
| `/frontend:page-new <name>`      | Create page component                                          |
| `/db:create <name>`              | Create database migration                                      |
| `/db:migrate`                    | Run pending migrations                                         |
| `/db:reset`                      | Reset database (WARNING: deletes data)                         |
| `/check:all`                     | Run all checks (lint, types, tests)                            |
| `/check:lint`                    | Run ESLint                                                     |
| `/check:types`                   | Run TypeScript check                                           |
| `/check:tests`                   | Run test suites                                                |

### Agents

| Agent                    | When to Use                                                 |
| ------------------------ | ----------------------------------------------------------- |
| `@code-reviewer`         | After completing significant code changes                   |
| `@security-auditor`      | Before deploying or after auth/API changes                  |
| `@performance-analyzer`  | Before optimizing or when performance issues arise          |
| `@pattern-enforcer`      | During code review or after generating code                 |
| `@api-designer`          | When planning new API endpoints                             |
| `@refactoring-expert`    | When code is getting unwieldy or before major changes       |
| `@requirements-analyst`  | Before starting feature development to clarify requirements |
| `@tech-stack-researcher` | When evaluating new libraries or technologies               |
| `@docs-generator`        | After completing features to generate documentation         |
| `@feature-orchestrator`  | Starting a new feature - guides through entire workflow     |

## Usage Examples

### Create a New Fullstack Feature

```
/fullstack:feature-new todo
```

This generates:

- Backend: model, schemas, service, router, tests
- Frontend: types, service, hooks, components, page
- Updates: main.py router registration, App.tsx route

### Quick Code Review

```
@code-reviewer review the changes in services/backend/app/routers/
```

### Security Audit Before Deploy

```
@security-auditor audit services/backend/app/
```

### Check Everything Before Commit

```
/check:all
```

### Clarify Requirements Before Building

```
@requirements-analyst I need to add a notifications system for users
```

### Evaluate New Technology

```
@tech-stack-researcher should we use Zustand or Jotai for state management?
```

### Refactor Complex Code

```
@refactoring-expert analyze services/backend/app/services/user_service.py for improvements
```

### Generate API Documentation

```
@docs-generator document the new files endpoint API
```

## MCP Servers

The plugin includes these MCP server integrations:

### Context7 (Documentation)

Get latest library documentation:

```
"use context7 to look up React 19 useTransition"
```

### Neon (PostgreSQL)

Manage Neon databases:

```
"show my Neon projects"
"create a new Neon branch for testing"
```

### Redis Cloud

Manage Redis databases:

```
"list my Redis databases"
"create a new Redis database"
```

**Required Environment Variables:**

```bash
export NEON_API_KEY="your-neon-api-key"
export REDIS_CLOUD_API_KEY="your-redis-api-key"
export REDIS_CLOUD_SECRET_KEY="your-redis-secret-key"
```

## File Structure

```
fullstack-template/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest with MCP config
├── commands/
│   ├── fullstack/           # E2E feature commands
│   ├── backend/             # Backend scaffolding
│   ├── frontend/            # Frontend scaffolding
│   ├── db/                  # Database operations
│   └── check/               # Code quality checks
├── agents/
│   ├── api-designer.md
│   ├── code-reviewer.md
│   ├── docs-generator.md
│   ├── feature-orchestrator.md
│   ├── pattern-enforcer.md
│   ├── performance-analyzer.md
│   ├── refactoring-expert.md
│   ├── requirements-analyst.md
│   ├── security-auditor.md
│   └── tech-stack-researcher.md
└── PLUGIN.md                # This file
```

## Conventions

All commands and agents follow the patterns documented in `CLAUDE.md`:

### Backend (Python)

- Async/await throughout
- Service layer pattern
- Soft delete with is_deleted flag
- SQLAlchemy 2.0 select() style
- Dependency injection

### Frontend (TypeScript)

- Feature-based architecture
- Custom hooks for logic
- Service layer for API calls
- No `any` types
- Barrel exports

## Contributing

To add new commands:

1. Create a `.md` file in the appropriate `commands/` subdirectory
2. Add YAML frontmatter with `description` and optionally `argument-hint`, `allowed-tools`
3. Write clear instructions for Claude to follow

To add new agents:

1. Create a `.md` file in `agents/`
2. Include: name, description, category in frontmatter
3. Define: Behavioral Mindset, Key Actions, Boundaries
