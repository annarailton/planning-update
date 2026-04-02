# Fullstack Template

React 19 + TypeScript + FastAPI + Neon PostgreSQL + Redis + GCP + Clerk Auth

## Commands

```bash
pnpm dev              # Start services (reads features.json)
pnpm dev:all          # Start ALL services
pnpm down             # Stop all
pnpm test:backend     # Backend tests
pnpm test:frontend    # Frontend tests
pnpm playwright --help  # Playwright CLI (project-standard replacement for MCP)
pnpm db:migrate       # Run migrations
pnpm db:create "msg"  # New migration
```

## Critical Rules

1. **Use pnpm scripts** - Never `cd services/x && command`. Use `docker compose exec backend uv add pkg`
2. **Use Settings class** - Never `os.getenv()`. Use `from core.config import get_settings`
3. **Use domain exceptions** - Never `HTTPException`. Use `NotFoundError`, `ValidationError`, etc
4. **No `any` types** - Define proper TypeScript interfaces
5. **Async everything** - All DB/external calls must be async
6. **Soft delete** - Use `is_deleted` flag, never hard delete
7. **Frontend side effects in hooks** - Keep `useEffect` out of page/feature components; put effect logic in custom hooks

## Architecture

```
services/
  backend/    # FastAPI → Cloud Run
  frontend/   # React SPA → Cloud Run
  worker/     # Background jobs → Cloud Run
packages/     # Shared Python packages
```

## Feature Flags

Edit `features.json` to enable: redis, worker, temporal, llm providers, langfuse

## Agents

Claude auto-spawns these as needed. Don't invoke manually.

**Quality** (run via `/clean-slop`):

- `code-reviewer` - Quality, patterns, types
- `pattern-enforcer` - CLAUDE.md compliance
- `security-auditor` - OWASP, auth, secrets
- `edge-case-auditor` - Error handling, failures
- `performance-analyzer` - N+1, memory, bottlenecks

**Design** (used during planning):

- `architect` - Complex features, multi-service changes
- `ux-critic` - UI/UX review
- `api-designer` - API endpoint design
- `requirements-analyst` - Vague → clear specs

**Implementation**:

- `implementor` - Code writing (spawn multiple in parallel)
- `refactoring-expert` - Code restructuring

**Utility**:

- `docs-generator` - Generate documentation
- `tech-stack-researcher` - Evaluate new dependencies

## Auto-Parallel Pattern

When implementing features with independent parts, spawn multiple `implementor` agents in parallel:

```
"Add user deletion"
       ↓
┌──────────┬──────────┬──────────┐
│ backend  │ frontend │ frontend │  (parallel)
│ service  │ hook     │ UI       │
└──────────┴──────────┴──────────┘
       ↓
  Verify integration
```

## User Commands

- `/clean-slop` - Quality-agent audit, fixes, and re-verification
- `/commit-push` - Review changes, create logical commits, and push
- `/check` - Lint, type checks, and tests across backend + frontend
- `/docs` - Docs updates for recent code changes
- `/format` - Format changed or specified files

## Skills (Auto-Load)

Claude auto-loads these when context matches. Also user-invocable:

- `/status` - Status, progress, and next-step summary from plan doc + git history
- `/temporal-workflow` - Temporal workflows for durable or long-running jobs
- `/db-migration` - Models + Alembic migrations for schema changes
- `/new-package` - Shared Python packages under `packages/`
- `/api-endpoint` - Backend API endpoint with schema, service, router, and test
- `/fullstack-feature` - Coordinated backend + frontend feature work
- `/redis-job` - Redis Streams enqueue + worker handler flows
- `/new-skill` - New Claude Code skills and slash-command guidance
- `/sync-configs` - Sync Claude/Codex configs without flattening platform wording

## Implementation Workflow

- Follow phases sequentially — never skip or jump ahead unless told
- Verify stubs are wired up before marking phase complete
- Simplest approach first — no speculative abstractions
- Status checks: read plan doc + git log, don't re-explore codebase
- `git rm --cached` + `.gitignore` when removing tracked files — both required

## Verification Before Done

- Never mark a task complete without evidence it works.
- Mandatory gate: run `/clean-slop` before marking any task done, fix all findings, and re-run until no findings remain.
- Use the lightest proof that matches risk and scope.
- Prefer walkthroughs/integration checks for user-facing flows.
- Use targeted tests when walkthrough evidence is weak or missing.
- For config/docs/sync changes, use consistency checks (for example `/sync-configs`) instead of new tests.

## Execution Protocol (LLM)

- Plan before implementation for non-trivial tasks (`>=3` steps, multi-service changes, or architecture/config-sync decisions).
- Re-plan immediately if first pass introduces drift/regression, scope changes materially, or the same verification fails twice.
- Keep changes minimal: touch only necessary files; avoid speculative refactors.

## Updating Patterns

**DUAL-UPDATE RULE**: This repo has parallel configs for Claude Code and Codex. When updating ANY config file, you MUST update its counterpart on the other side.

### File Pair Mapping

| Claude Code                 | Codex                         | Notes                                    |
| --------------------------- | ----------------------------- | ---------------------------------------- |
| `CLAUDE.md`                 | `AGENTS.md`                   | `/cmd` → `$cmd`, "Claude" → "Codex"      |
| `services/*/CLAUDE.md`      | `services/*/AGENTS.md`        | Content identical                        |
| `packages/CLAUDE.md`        | `packages/AGENTS.md`          | Content identical                        |
| `packages/db/CLAUDE.md`     | `packages/db/AGENTS.md`       | Content identical                        |
| `.claude/skills/*/SKILL.md` | `.agents/skills/*/SKILL.md`   | Shared intent synced; platform wording may differ |
| `.claude/agents/*.md`       | `.codex/agents/*.toml`        | MD→TOML: body → `developer_instructions` |
| `.claude/commands/*.md`     | `.agents/skills/*/SKILL.md`   | Commands become skills                   |
| `.claude/rules/*.md`        | Sections in `AGENTS.md` files | Rules merged into docs                   |
| `.claude/hooks/*.sh`        | `.codex/scripts/*.sh`         | Nearly identical scripts                 |

### Translation Rules

**Skills** (`.claude/skills/` ↔ `.agents/skills/`):

- Claude has extra frontmatter: `disable-model-invocation`, `user-invocable`, `allowed-tools`
- Codex has only: `name`, `description`
- Keep shared workflow, examples, and coverage in sync
- Preserve platform-native wording and discovery cues:
  - Claude skills should be written for Claude auto-load and slash-command usage
  - Codex skills should be written for Codex skill discovery and usage
  - Translate invocation syntax (`/skill` ↔ `$skill`), tool naming, and metadata instead of forcing identical prose
- When syncing, compare normalized meaning and structure, not literal body equality

**Agents** (`.claude/agents/*.md` ↔ `.codex/agents/*.toml`):

- Claude: YAML frontmatter (`name`, `description`, `tools`, `category`, `skills`) + markdown body
- Codex: TOML with `sandbox_mode`, `model_reasoning_effort`, `developer_instructions` (body)
- Claude `skills:` field has no Codex equivalent — Codex makes all skills globally visible to all agents. No TOML update needed when adding/changing `skills:`.
- When updating agent logic, update the body/instructions on BOTH sides

**Commands → Skills** (`.claude/commands/*.md` ↔ `.agents/skills/*/SKILL.md`):

- Claude keeps commands separate; Codex merged them into skills
- `check.md` ↔ `check/SKILL.md`, `clean-slop.md` ↔ `clean-slop/SKILL.md`, etc.

**Rules** (`.claude/rules/*.md` ↔ AGENTS.md sections):

- `rules/testing.md` → "Verification Before Done", "Execution Protocol (LLM)", and "Testing Rules" sections in root `AGENTS.md`
- `rules/env-vars.md` → "Environment Variables" section in root `AGENTS.md`
- `rules/backend.md` → merged into `services/backend/AGENTS.md`
- `rules/frontend.md` → merged into `services/frontend/AGENTS.md`
- `rules/database.md` → `packages/db/AGENTS.md`

Run `/sync-configs` to verify both sides are in sync.

### Single-Side Updates

When you discover a reusable pattern, update ALL relevant files on BOTH sides:

```
Learning: "Always use AbortController for fetches"
→ .claude/rules/frontend.md (Claude rule)
→ services/frontend/CLAUDE.md (Claude example)
→ .claude/skills/fullstack-feature/SKILL.md (Claude skill template)
→ services/frontend/AGENTS.md (Codex example)
→ .agents/skills/fullstack-feature/SKILL.md (Codex skill template)
→ Root AGENTS.md if it affects Testing/Env sections
```

**Guidelines:**

- Update all relevant locations on BOTH sides
- Keep concise - patterns, not prose
- Commit together: `docs: add AbortController pattern`

## See Also

@services/backend/CLAUDE.md
@services/frontend/CLAUDE.md
@services/worker/CLAUDE.md
@packages/CLAUDE.md
