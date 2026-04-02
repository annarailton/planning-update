---
name: commit-push
description: Review local changes, split them into logical commits, and push the current branch. Use when the user asks to commit, push, or clean up history.
---

# Commit & Push

Use this only when the user explicitly wants commit or push work.
Optimize for clean commit grouping and accurate commit messages, not for minimizing commit count.

**No AI references** - no Co-Authored-By, no Claude mentions.

## Steps

1. **Analyze**

   ```bash
   git status && git diff --stat && git diff --stat --staged
   ```

2. **Group by**:
   - Package/feature (related files together)
   - Type (feat, fix, refactor, docs, test, chore)

3. **Commit each group**:

   ```bash
   git add <files>
   git commit -m "type: description"
   ```

4. **Push**:
   ```bash
   git push  # or: git push -u origin $(git branch --show-current)
   ```

## Types

`feat` | `fix` | `refactor` | `docs` | `test` | `chore`

## Rules

- Never mix unrelated changes
- Atomic commits (independently reversible)
- Meaningful messages (why, not what)
- Check for secrets before commit
- Verify: `git log --oneline -5`
