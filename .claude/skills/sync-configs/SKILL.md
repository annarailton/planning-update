---
name: sync-configs
description: Verify and sync Claude Code and Codex config pairs while preserving platform-specific wording. Auto-loads for CLAUDE.md, AGENTS.md, skills, agents, rules, or commands changes.
disable-model-invocation: false
user-invocable: true
---

# Sync Configs

Use this for paired Claude/Codex config work.
Sync shared intent and examples, but keep platform-native wording, metadata, and invocation syntax intact.

## File Pair Mapping

| Claude Code                 | Codex                       | Comparison                               |
| --------------------------- | --------------------------- | ---------------------------------------- |
| `CLAUDE.md`                 | `AGENTS.md`                 | Structural (translate `/cmd` to `$cmd`) |
| `services/*/CLAUDE.md`      | `services/*/AGENTS.md`      | Content identical                        |
| `packages/CLAUDE.md`        | `packages/AGENTS.md`        | Content identical                        |
| `packages/db/CLAUDE.md`     | `packages/db/AGENTS.md`     | Content identical                        |
| `.claude/skills/*/SKILL.md` | `.agents/skills/*/SKILL.md` | Shared intent synced; platform wording may differ |
| `.claude/agents/*.md`       | `.codex/agents/*.toml`      | Extract body/instructions for comparison |
| `.claude/commands/*.md`     | `.agents/skills/*/SKILL.md` | Commands map to skills                   |
| `.claude/rules/*.md`        | Sections in `AGENTS.md`     | Rules map to doc sections                |
| `.claude/hooks/*.sh`        | `.codex/scripts/*.sh`       | Nearly identical                         |

## 1. Skills Sync

For each `.claude/skills/*/`:
1. Read both `.claude/skills/{name}/SKILL.md` and `.agents/skills/{name}/SKILL.md`
2. Strip frontmatter, then compare normalized structure and meaning
3. Claude-only fields (`disable-model-invocation`, `user-invocable`, `allowed-tools`, slash-command UX) stay Claude-native
4. Codex wording, trigger language, and `$skill` invocation stay Codex-native
5. Report only real drift in workflow, examples, scope, or missing coverage

For each `.agents/skills/*/`:
1. Check for `.claude/skills/{name}/SKILL.md` or `.claude/commands/{name}.md`
2. Report missing counterparts

## 2. Agents Sync

For each `.claude/agents/*.md`:
1. Extract markdown body (after YAML frontmatter)
2. Find `.codex/agents/*.toml`, extract `developer_instructions`
3. Compare body/instructions
4. Report differences

## 3. Service/Package Docs

Compare each pair (should be identical):
- `services/backend/CLAUDE.md` / `services/backend/AGENTS.md`
- `services/frontend/CLAUDE.md` / `services/frontend/AGENTS.md`
- `services/worker/CLAUDE.md` / `services/worker/AGENTS.md`
- `packages/CLAUDE.md` / `packages/AGENTS.md`
- `packages/db/CLAUDE.md` / `packages/db/AGENTS.md`

## 4. Rules to AGENTS.md Sections

- `.claude/rules/testing.md` -> "Testing Rules" in root `AGENTS.md`
- `.claude/rules/env-vars.md` -> "Environment Variables" in root `AGENTS.md`
- `.claude/rules/backend.md` -> `services/backend/AGENTS.md`
- `.claude/rules/frontend.md` -> `services/frontend/AGENTS.md`
- `.claude/rules/database.md` -> `packages/db/AGENTS.md`

## 5. Hooks/Scripts

Compare `.claude/hooks/*.sh` with `.codex/scripts/*.sh`. Functionally identical (may differ in emoji vs text).

## 6. Fix Drift

For each difference:
1. Show file pair and diff
2. Separate platform-specific wording from shared workflow
3. Prefer the side with better shared guidance as source of truth for intent, not literal phrasing
4. Apply translation rules from CLAUDE.md "Updating Patterns"
5. Preserve valid Claude-only and Codex-only optimizations

### Translation Reference

| From                     | To                      | Transform                                |
| ------------------------ | ----------------------- | ---------------------------------------- |
| Claude skill frontmatter | Codex skill frontmatter | Keep only `name`, `description`; do not copy Claude-only fields |
| Claude agent `.md`       | Codex agent `.toml`     | YAML->TOML, body->`developer_instructions` |
| Claude command `.md`     | Codex skill `SKILL.md`  | Add `name`/`description` frontmatter     |
| Claude rule `.md`        | AGENTS.md section       | Merge content into appropriate section   |
| `/command` references    | `$command` references   | Replace prefix                           |
| "Claude" references      | "Codex" references      | Replace tool name                        |
| Claude skill body        | Codex skill body        | Preserve intent/examples, rewrite for Codex-native discovery and invocation |
