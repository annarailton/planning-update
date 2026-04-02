---
name: new-skill
description: Create or update a Codex skill (SKILL.md). Use when adding reusable Codex instructions, skill templates, or Codex-specific guidance.
---

# New Skill

Use this to create reusable Codex-first instructions instead of re-explaining the same workflow in chat.
Each skill = directory with `SKILL.md`. Extends Codex with reusable instructions.

```
.agents/skills/<skill-name>/
├── SKILL.md           # Main instructions (required)
├── reference.md       # Detailed docs (optional)
├── examples/          # Example outputs (optional)
└── scripts/           # Helper scripts (optional)
```

## 1. Choose Scope

- Codex skill only: create `.agents/skills/<skill-name>/SKILL.md`
- Shared skill: create/update both `.agents/skills/<skill-name>/SKILL.md` and `.claude/skills/<skill-name>/SKILL.md`
- Codex command-style utility: create/update `.agents/skills/<skill-name>/SKILL.md` and map it to `.claude/commands/<skill-name>.md` if Claude exposes it as a command instead of a skill

## 2. Create SKILL.md

### Frontmatter

```yaml
---
name: my-skill # Lowercase, hyphens only (max 64 chars). Defaults to directory name
description: What it does and when to use it
---
```

Key fields:
- `description` -- most important; keep it concise and searchable for Codex users
- Codex frontmatter stays minimal: only `name`, `description`
- Put platform-specific invocation notes in the body, not in custom frontmatter

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

### Platform Notes

- Codex skills in this repo are instruction documents, not Claude-style slash-command templates
- Do not add Claude-specific interpolation syntax, slash-command examples, or Claude-only metadata to Codex skills
- If the skill also exists on Claude, keep the shared workflow aligned but rewrite examples in Codex-native terms

## 3. Project Conventions

Skills in this codebase:
- Include code templates with exact file paths
- Reference other skills for overlapping patterns (e.g., "use api-endpoint skill")
- Show file structure as ASCII tree
- Note prerequisites (feature flags, dependencies)
- Keep SKILL.md under 500 lines; use supporting files for reference
- Write Codex-side instructions for Codex first: use `$skill-name` references, Codex terminology, and Codex tool assumptions
- If the skill has a Claude counterpart, sync the shared workflow but keep Claude-specific auto-load, slash-command, and frontmatter guidance on the Claude side

Standard frontmatter:

```yaml
---
name: skill-name
description: Brief description. Use when [task or context].
---
```

## 4. Register in AGENTS.md

- Root `AGENTS.md` -- add to the Skills list
- Service-specific `AGENTS.md` -- if skill-scoped
- If there is a Claude counterpart, update `CLAUDE.md` and its skill or command file in the same change

## 5. Test

1. Start a fresh Codex session if needed so the updated skill inventory is visible
2. Check the skill appears in the available-skills list
3. Mention the skill by name or with `$skill-name` in a request and verify Codex can follow it
4. If there is a Claude counterpart, verify the paired Claude file still matches the same shared workflow

## Verify

- Description is concise and searchable for Codex users
- Code templates use project conventions (Settings class, domain exceptions, etc.)
- File paths accurate for codebase structure
- Supporting files referenced if >500 lines
- Registered in root `AGENTS.md`
- Claude counterpart updated only where shared intent must stay aligned
