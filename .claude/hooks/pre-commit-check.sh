#!/bin/bash
# Quick quality check before commit - NOT full clean-slop
# Returns warnings via stdout (Claude sees them)
# Exit 0 = proceed, Exit 2 = block

# Get staged files (null-terminated for safety with spaces)
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || echo "")

if [ -z "$STAGED_FILES" ]; then
  exit 0
fi

ISSUES=""

# Check TypeScript files for 'any' type
TS_FILES=$(printf '%s\n' "$STAGED_FILES" | grep -E '\.(ts|tsx)$' || true)
if [ -n "$TS_FILES" ]; then
  ANY_USAGE=$(printf '%s\n' "$TS_FILES" | while IFS= read -r f; do grep -l ': any' "$f" 2>/dev/null; done | head -3 || true)
  if [ -n "$ANY_USAGE" ]; then
    ISSUES="$ISSUES
⚠️  'any' type found in: $ANY_USAGE"
  fi

  # Check for console.log (should use logger)
  CONSOLE_LOG=$(printf '%s\n' "$TS_FILES" | while IFS= read -r f; do grep -l 'console\.log' "$f" 2>/dev/null; done | head -3 || true)
  if [ -n "$CONSOLE_LOG" ]; then
    ISSUES="$ISSUES
⚠️  console.log found in: $CONSOLE_LOG (use logger instead)"
  fi
fi

# Check Python files for os.getenv (should use Settings)
PY_FILES=$(printf '%s\n' "$STAGED_FILES" | grep -E '\.py$' || true)
if [ -n "$PY_FILES" ]; then
  GETENV=$(printf '%s\n' "$PY_FILES" | while IFS= read -r f; do grep -l 'os\.getenv\|os\.environ' "$f" 2>/dev/null; done | head -3 || true)
  if [ -n "$GETENV" ]; then
    ISSUES="$ISSUES
⚠️  os.getenv found in: $GETENV (use Settings class instead)"
  fi

  # Check for HTTPException (should use domain exceptions)
  HTTP_EXC=$(printf '%s\n' "$PY_FILES" | while IFS= read -r f; do grep -l 'raise HTTPException' "$f" 2>/dev/null; done | head -3 || true)
  if [ -n "$HTTP_EXC" ]; then
    ISSUES="$ISSUES
⚠️  HTTPException found in: $HTTP_EXC (use domain exceptions instead)"
  fi
fi

# Check for potential secrets
SECRET_PATTERNS='(api_key|apikey|secret|password|token)\s*=\s*["\047][^"\047]{8,}'
SECRETS=$(printf '%s\n' "$STAGED_FILES" | while IFS= read -r f; do grep -ilE "$SECRET_PATTERNS" "$f" 2>/dev/null; done | head -3 || true)
if [ -n "$SECRETS" ]; then
  ISSUES="$ISSUES
🔴 Potential hardcoded secrets in: $SECRETS"
fi

# Check config sync (Claude ↔ Codex)
if [ -f "scripts/check-config-sync.sh" ]; then
  bash scripts/check-config-sync.sh
fi

# Output issues (Claude sees this)
if [ -n "$ISSUES" ]; then
  printf "Pre-commit check found issues:%s\n" "$ISSUES"
  printf "\nConsider running /clean-slop for full review before committing.\n"
  exit 0
fi

exit 0
