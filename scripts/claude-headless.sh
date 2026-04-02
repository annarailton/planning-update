#!/bin/bash
# Claude Code headless aliases — source in .zshrc
# Usage: source /path/to/fullstack-template/scripts/claude-headless.sh

# Quick quality checks (run in background, output to temp file)
cc-check() {
  local out=$(mktemp /tmp/cc-check.XXXXXX)
  echo "Running /check in background → $out"
  claude -p "/check" --output-format text > "$out" 2>&1 &
  echo "PID: $!"
}

cc-sync() {
  local out=$(mktemp /tmp/cc-sync.XXXXXX)
  echo "Running /sync-configs in background → $out"
  claude -p "/sync-configs" --output-format text > "$out" 2>&1 &
  echo "PID: $!"
}

cc-slop() {
  local out=$(mktemp /tmp/cc-slop.XXXXXX)
  echo "Running /clean-slop in background → $out"
  claude -p "/clean-slop" --output-format text > "$out" 2>&1 &
  echo "PID: $!"
}

# Review current diff before push
cc-review() {
  echo "Reviewing changes..."
  git diff HEAD~1 2>/dev/null | claude -p \
    "Review this diff. Check for: CLAUDE.md violations, security issues, type safety, missing error handling. Be concise — pass/fail with specific issues." \
    --output-format text
}

# Generate PR description from commits
cc-pr-desc() {
  local base="${1:-main}"
  git log "$base"..HEAD --oneline | claude -p \
    "Generate a concise PR description from these commits. Use ## Summary with bullet points and ## Test Plan with checklist." \
    --output-format text
}
