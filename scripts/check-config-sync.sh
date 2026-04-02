#!/bin/bash
# Check that Claude Code and Codex configs are updated together.
# Called by both pre-commit hooks. Warns but does NOT block (exit 0).

STAGED_FILES=$(git diff --cached --name-only 2>/dev/null || echo "")

if [ -z "$STAGED_FILES" ]; then
  exit 0
fi

WARNINGS=""

# Helper: check if a file is staged
is_staged() {
  echo "$STAGED_FILES" | grep -qF "$1"
}

# Helper: warn about missing counterpart
warn_missing() {
  local staged="$1"
  local expected="$2"
  if is_staged "$staged" && ! is_staged "$expected"; then
    WARNINGS="$WARNINGS
  $staged staged but $expected is not"
  fi
}

# --- Root docs ---
warn_missing "CLAUDE.md" "AGENTS.md"
warn_missing "AGENTS.md" "CLAUDE.md"

# --- Service docs ---
for svc in backend frontend worker; do
  warn_missing "services/$svc/CLAUDE.md" "services/$svc/AGENTS.md"
  warn_missing "services/$svc/AGENTS.md" "services/$svc/CLAUDE.md"
done

# --- Package docs ---
warn_missing "packages/CLAUDE.md" "packages/AGENTS.md"
warn_missing "packages/AGENTS.md" "packages/CLAUDE.md"
warn_missing "packages/db/CLAUDE.md" "packages/db/AGENTS.md"
warn_missing "packages/db/AGENTS.md" "packages/db/CLAUDE.md"

# --- Skills (check both directions) ---
# Extract skill names from staged .claude/skills/*/SKILL.md paths
CLAUDE_SKILLS=$(echo "$STAGED_FILES" | sed -n 's|^\.claude/skills/\([^/]*\)/SKILL\.md$|\1|p' || true)
for skill in $CLAUDE_SKILLS; do
  warn_missing ".claude/skills/$skill/SKILL.md" ".agents/skills/$skill/SKILL.md"
done

CODEX_SKILLS=$(echo "$STAGED_FILES" | sed -n 's|^\.agents/skills/\([^/]*\)/SKILL\.md$|\1|p' || true)
for skill in $CODEX_SKILLS; do
  warn_missing ".agents/skills/$skill/SKILL.md" ".claude/skills/$skill/SKILL.md"
done

# --- Agents (md <-> toml) ---
CLAUDE_AGENTS=$(echo "$STAGED_FILES" | sed -n 's|^\.claude/agents/\([^.]*\)\.md$|\1|p' || true)
for agent in $CLAUDE_AGENTS; do
  warn_missing ".claude/agents/$agent.md" ".codex/agents/$agent.toml"
done

CODEX_AGENTS=$(echo "$STAGED_FILES" | sed -n 's|^\.codex/agents/\([^.]*\)\.toml$|\1|p' || true)
for agent in $CODEX_AGENTS; do
  warn_missing ".codex/agents/$agent.toml" ".claude/agents/$agent.md"
done

# --- Commands <-> Skills ---
CLAUDE_CMDS=$(echo "$STAGED_FILES" | sed -n 's|^\.claude/commands/\([^.]*\)\.md$|\1|p' || true)
for cmd in $CLAUDE_CMDS; do
  warn_missing ".claude/commands/$cmd.md" ".agents/skills/$cmd/SKILL.md"
done

# --- Hooks <-> Scripts ---
CLAUDE_HOOKS=$(echo "$STAGED_FILES" | sed -n 's|^\.claude/hooks/\(.*\.sh\)$|\1|p' || true)
for hook in $CLAUDE_HOOKS; do
  warn_missing ".claude/hooks/$hook" ".codex/scripts/$hook"
done

CODEX_SCRIPTS=$(echo "$STAGED_FILES" | sed -n 's|^\.codex/scripts/\(.*\.sh\)$|\1|p' || true)
for script in $CODEX_SCRIPTS; do
  warn_missing ".codex/scripts/$script" ".claude/hooks/$script"
done

# --- Rules -> AGENTS.md (generic warning) ---
CLAUDE_RULES=$(echo "$STAGED_FILES" | grep '\.claude/rules/.*\.md' || true)
if [ -n "$CLAUDE_RULES" ] && ! is_staged "AGENTS.md"; then
  has_service_agents=false
  for svc_agents in services/backend/AGENTS.md services/frontend/AGENTS.md packages/db/AGENTS.md; do
    if is_staged "$svc_agents"; then
      has_service_agents=true
    fi
  done
  if [ "$has_service_agents" = false ]; then
    WARNINGS="$WARNINGS
  Claude rules changed but no AGENTS.md files staged (rules content lives in AGENTS.md sections)"
  fi
fi

# --- Output ---
if [ -n "$WARNINGS" ]; then
  printf "Config sync warning - these file pairs may need dual-updates:\n%s\n" "$WARNINGS"
  printf "\nRun /sync-configs (Claude) or \$sync-configs (Codex) to verify sync.\n"
fi

exit 0
