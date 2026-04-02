---
name: new-skill
description: Create or update a Claude Code skill (SKILL.md). Auto-loads for new skills, slash commands, or Claude-specific skill guidance.
disable-model-invocation: false
user-invocable: true
---

# New Skill

Use this to create reusable Claude-first instructions instead of repeating the same workflow manually.
Each skill = directory with `SKILL.md`. Extends Claude with reusable instructions.

```
.claude/skills/<skill-name>/
├── SKILL.md           # Main instructions (required)
├── reference.md       # Detailed docs (optional)
├── examples/          # Example outputs (optional)
└── scripts/           # Helper scripts (optional)
```

## 1. Choose Skill Type

| Type          | `disable-model-invocation` | `user-invocable` | Use Case                                       |
| ------------- | -------------------------- | ---------------- | ---------------------------------------------- |
| Auto + Manual | `false`                    | `true`           | Claude auto-loads + user `/invoke`             |
| Manual Only   | `true`                     | `true`           | User-triggered only (deploy, destructive)      |
| Auto Only     | `false`                    | `false`          | Background knowledge, hidden from `/` menu     |

## 2. Create SKILL.md

### Frontmatter

```yaml
---
name: my-skill # Lowercase, hyphens only (max 64 chars). Defaults to directory name
description: What it does and when # Claude uses this to decide when to auto-load
disable-model-invocation: false # true = only user can invoke via /name
user-invocable: true # false = hidden from / menu, only Claude invokes
allowed-tools: Read, Grep, Bash # Restrict tools when skill is active (optional)
argument-hint: "[name] [type]" # Shown in autocomplete (optional)
model: opus # Override model (optional)
context: fork # Run in isolated subagent (optional)
agent: Explore # Subagent type when context: fork (optional)
---
```

Key fields:
- `description` -- most important; Claude uses it to decide when to load
- `allowed-tools` -- grants tools without per-use approval when active
- `context: fork` -- isolated execution (no conversation history); only for self-contained tasks
- `agent` options: `Explore`, `Plan`, `general-purpose`, or custom from `.claude/agents/`

### Body Content

Two styles:

**Reference** -- conventions applied to current work:

```markdown
When writing API endpoints:

- Use RESTful naming conventions
- Return consistent error formats
```

**Task** -- step-by-step process:

```markdown
# Creating a Widget

## Step 1: Define Types

...code template...

## Step 2: Implement Service

...code template...
```

### String Substitutions

| Variable                | Description                        |
| ----------------------- | ---------------------------------- |
| `$ARGUMENTS`            | All text after `/skill-name`       |
| `$ARGUMENTS[N]` or `$N` | Specific argument by 0-based index |
| `${CLAUDE_SESSION_ID}`  | Current session ID                 |

Example: `/migrate-component SearchBar React Vue` -- `$0` = `SearchBar`, `$1` = `React`, `$2` = `Vue`

If `$ARGUMENTS` is not in content, arguments appended as `ARGUMENTS: <value>`.

### Dynamic Context Injection

`` !`command` `` runs shell commands before content is sent to Claude:

```markdown
Current branch: !`git branch --show-current`
Recent changes: !`git diff --stat HEAD~5`
```

## 3. Project Conventions

Skills in this codebase:
- Include code templates with exact file paths
- Reference other skills for overlapping patterns (e.g., "use api-endpoint skill")
- Show file structure as ASCII tree
- Note prerequisites (feature flags, dependencies)
- Keep SKILL.md under 500 lines; use supporting files for reference
- Write Claude-side instructions for Claude first: use `/skill-name`, Claude terminology, and Claude auto-load guidance
- If the skill has a Codex counterpart, keep the shared workflow aligned but preserve Codex-native wording and minimal frontmatter on the Codex side

Standard frontmatter:

```yaml
---
name: skill-name
description: Brief description. Auto-loads when [context keywords].
disable-model-invocation: false
user-invocable: true
---
```

## 4. Register in CLAUDE.md

- Root `CLAUDE.md` -- add to Skills table
- Service-specific `CLAUDE.md` -- if service-scoped
- `.claude/settings.json` -- if skill needs special permissions

## 5. Test

1. Restart Claude Code (skills load on startup)
2. "What skills are available?" -- verify it appears
3. Test auto-loading with matching context
4. Test `/skill-name` manual invocation
5. `/context` -- check skill not excluded by character budget

## Verify

- Description includes keywords Claude will match on
- Frontmatter fields match intended invocation type
- Code templates use project conventions (Settings class, domain exceptions, etc.)
- File paths accurate for codebase structure
- Supporting files referenced if >500 lines
- Registered in root CLAUDE.md
