#!/bin/bash
# Auto-format source files
# Usage: auto-format.sh [file1 file2 ...] (or no args for all changed files)

set -euo pipefail

if [ $# -gt 0 ]; then
    FILES="$@"
else
    # Get changed files (staged + unstaged)
    FILES=$(git diff --name-only HEAD 2>/dev/null || echo "")
    STAGED=$(git diff --cached --name-only 2>/dev/null || echo "")
    FILES=$(printf '%s\n%s' "$FILES" "$STAGED" | sort -u | grep -v '^$' || true)
fi

if [ -z "$FILES" ]; then
    echo "No files to format"
    exit 0
fi

# Format TypeScript/JavaScript files
TS_FILES=$(printf '%s\n' $FILES | grep -E '\.(ts|tsx|js|jsx)$' || true)
if [ -n "$TS_FILES" ]; then
    echo "Formatting TypeScript/JavaScript files..."
    echo "$TS_FILES" | xargs npx prettier --write 2>/dev/null || true
fi

# Format Python files
PY_FILES=$(printf '%s\n' $FILES | grep -E '\.py$' || true)
if [ -n "$PY_FILES" ]; then
    echo "Formatting Python files..."
    echo "$PY_FILES" | xargs ruff format 2>/dev/null || true
fi

echo "Done."
