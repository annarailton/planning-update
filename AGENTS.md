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
  backend/    # FastAPI -> Cloud Run
  frontend/   # React SPA -> Cloud Run
  worker/     # Background jobs -> Cloud Run
packages/     # Shared Python packages
```

## Feature Flags

Edit `features.json` to enable: redis, worker, temporal, llm providers, langfuse

## Agents

Codex auto-spawns these as needed. Don't invoke manually.

**Quality** (run via `$clean-slop`):

- `code-reviewer` - Quality, patterns, types
- `pattern-enforcer` - AGENTS.md compliance
- `security-auditor` - OWASP, auth, secrets
- `edge-case-auditor` - Error handling, failures
- `performance-analyzer` - N+1, memory, bottlenecks

**Design** (used during planning):

- `architect` - Complex features, multi-service changes
- `ux-critic` - UI/UX review
- `api-designer` - API endpoint design
- `requirements-analyst` - Vague -> clear specs

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
       |
+-----------+-----------+-----------+
| backend   | frontend  | frontend  |  (parallel)
| service   | hook      | UI        |
+-----------+-----------+-----------+
       |
  Verify integration
```

## Skills

Invoke with `$skill-name`:

- `$status` - Status, progress, and next-step summary from plan doc + git history
- `$temporal-workflow` - Temporal workflows for durable or long-running jobs
- `$db-migration` - Models + Alembic migrations for schema changes
- `$new-package` - Shared Python packages under `packages/`
- `$api-endpoint` - Backend API endpoint with schema, service, router, and test
- `$fullstack-feature` - Coordinated backend + frontend feature work
- `$redis-job` - Redis Streams enqueue + worker handler flows
- `$clean-slop` - Quality-agent audit, fixes, and re-verification
- `$check` - Lint, type checks, and tests across backend + frontend
- `$commit-push` - Review changes, create logical commits, and push
- `$docs` - Docs updates for recent code changes
- `$format` - Format changed or specified files
- `$sync-configs` - Sync Codex/Claude configs without flattening platform wording

## Implementation Workflow

- Follow phases sequentially — never skip or jump ahead unless told
- Verify stubs are wired up before marking phase complete
- Simplest approach first — no speculative abstractions
- Status checks: read plan doc + git log, don't re-explore codebase
- `git rm --cached` + `.gitignore` when removing tracked files — both required

## Verification Before Done

- Never mark a task complete without evidence it works.
- Mandatory gate: run `$clean-slop` before marking any task done, fix all findings, and re-run until no findings remain.
- Use the lightest proof that matches risk and scope.
- Prefer walkthroughs/integration checks for user-facing flows.
- Use targeted tests when walkthrough evidence is weak or missing.
- For config/docs/sync changes, use consistency checks (for example `$sync-configs`) instead of new tests.

## Execution Protocol (LLM)

- Plan before implementation for non-trivial tasks (`>=3` steps, multi-service changes, or architecture/config-sync decisions).
- Re-plan immediately if first pass introduces drift/regression, scope changes materially, or the same verification fails twice.
- Keep changes minimal: touch only necessary files; avoid speculative refactors.

## Testing Rules

### Commands

```bash
pnpm test:backend     # Backend pytest
pnpm test:frontend    # Frontend vitest
```

### Backend (pytest)

- Async tests with `@pytest.mark.asyncio`
- Fixtures in `conftest.py`
- Mock external services (LLM, storage)
- Test success + error paths

```python
@pytest.mark.asyncio
async def test_create_user(db_session):
    service = UserService()
    user = await service.create(UserCreate(email="test@test.com"), db_session)
    assert user.email == "test@test.com"
```

### Frontend (vitest)

- React Testing Library for components
- Mock API calls with MSW or vi.mock
- Test user interactions, not implementation

```typescript
test('shows user name', async () => {
  render(<UserCard user={mockUser} />);
  expect(screen.getByText(mockUser.name)).toBeInTheDocument();
});
```

## Environment Variables

### Locations

1. `environment/.env.*.example` - Local dev examples
2. GitHub Secrets - CI/CD
3. `terraform/services/*/variables.tf` - Variable definition
4. `terraform/services/*/main.tf` - Pass to Cloud Run
5. `.github/workflows/_*.yml` - `TF_VAR_*` prefix

### Prefixes

- Frontend: `VITE_` prefix required
- Terraform: `TF_VAR_` prefix in GitHub Actions
- Sensitive: `sensitive = true` in Terraform

### Adding New Vars

1. Add to `environment/.env.backend.example`
2. Add to `core/config.py` Settings class
3. Add to `terraform/services/*/variables.tf`
4. Add to GitHub Secrets/Variables
5. Pass in workflow with `TF_VAR_` prefix

## Updating Patterns

**DUAL-UPDATE RULE**: This repo has parallel configs for Codex and Claude Code. When updating ANY config file, you MUST update its counterpart on the other side.

### File Pair Mapping

| Codex                         | Claude Code                 | Notes                                    |
| ----------------------------- | --------------------------- | ---------------------------------------- |
| `AGENTS.md`                   | `CLAUDE.md`                 | `$cmd` → `/cmd`, "Codex" → "Claude"      |
| `services/*/AGENTS.md`        | `services/*/CLAUDE.md`      | Content identical                        |
| `packages/AGENTS.md`          | `packages/CLAUDE.md`        | Content identical                        |
| `packages/db/AGENTS.md`       | `packages/db/CLAUDE.md`     | Content identical                        |
| `.agents/skills/*/SKILL.md`   | `.claude/skills/*/SKILL.md` | Shared intent synced; platform wording may differ |
| `.codex/agents/*.toml`        | `.claude/agents/*.md`       | TOML→MD: `developer_instructions` → body |
| `.agents/skills/*/SKILL.md`   | `.claude/commands/*.md`     | Skills become commands                   |
| Sections in `AGENTS.md` files | `.claude/rules/*.md`        | Docs split into rules                    |
| `.codex/scripts/*.sh`         | `.claude/hooks/*.sh`        | Nearly identical scripts                 |

### Translation Rules

**Skills** (`.agents/skills/` ↔ `.claude/skills/`):

- Codex has only: `name`, `description`
- Claude has extra frontmatter: `disable-model-invocation`, `user-invocable`, `allowed-tools`
- Keep shared workflow, examples, and coverage in sync
- Preserve platform-native wording and discovery cues:
  - Codex skills should be written for Codex skill discovery and usage
  - Claude skills should be written for Claude auto-load and slash-command usage
  - Translate invocation syntax (`$skill` ↔ `/skill`), tool naming, and metadata instead of forcing identical prose
- When syncing, compare normalized meaning and structure, not literal body equality

**Agents** (`.codex/agents/*.toml` ↔ `.claude/agents/*.md`):

- Codex: TOML with `sandbox_mode`, `model_reasoning_effort`, `developer_instructions` (body)
- Claude: YAML frontmatter (`name`, `description`, `tools`, `category`, `skills`) + markdown body
- Claude `skills:` field has no Codex equivalent — Codex makes all skills globally visible to all agents. No TOML update needed when adding/changing `skills:`.
- When updating agent logic, update the body/instructions on BOTH sides

**Skills → Commands** (`.agents/skills/*/SKILL.md` ↔ `.claude/commands/*.md`):

- Codex merged commands into skills; Claude keeps commands separate
- `check/SKILL.md` ↔ `check.md`, `clean-slop/SKILL.md` ↔ `clean-slop.md`, etc.

**AGENTS.md sections → Rules** (AGENTS.md sections ↔ `.claude/rules/*.md`):

- "Verification Before Done", "Execution Protocol (LLM)", and "Testing Rules" sections in root `AGENTS.md` → `rules/testing.md`
- "Environment Variables" section in root `AGENTS.md` → `rules/env-vars.md`
- `services/backend/AGENTS.md` → merged from `rules/backend.md`
- `services/frontend/AGENTS.md` → merged from `rules/frontend.md`
- `packages/db/AGENTS.md` → `rules/database.md`

Run `$sync-configs` to verify both sides are in sync.

### Single-Side Updates

When you discover a reusable pattern, update ALL relevant files on BOTH sides:

```
Learning: "Always use AbortController for fetches"
→ services/frontend/AGENTS.md (Codex example)
→ .agents/skills/fullstack-feature/SKILL.md (Codex skill template)
→ Root AGENTS.md if it affects Testing/Env sections
→ .claude/rules/frontend.md (Claude rule)
→ services/frontend/CLAUDE.md (Claude example)
→ .claude/skills/fullstack-feature/SKILL.md (Claude skill template)
```

**Guidelines:**

- Update all relevant locations on BOTH sides
- Keep concise - patterns, not prose
- Commit together: `docs: add AbortController pattern`

## See Also

@services/backend/AGENTS.md
@services/frontend/AGENTS.md
@services/worker/AGENTS.md
@packages/AGENTS.md
