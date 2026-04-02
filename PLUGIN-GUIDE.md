# Claude Code Plugin - Usage Guide

A practical guide to getting the best results from the fullstack-template Claude Code plugin.

## Quick Start

### First Time Setup

1. **Install Claude Code CLI** (if not already installed)

   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

2. **Set up MCP servers** (optional but recommended)

   ```bash
   export NEON_API_KEY="your-neon-api-key"
   export REDIS_CLOUD_API_KEY="your-redis-api-key"
   export REDIS_CLOUD_SECRET_KEY="your-redis-secret-key"
   ```

3. **Start Claude Code in your project**
   ```bash
   cd fullstack-template
   claude
   ```

The plugin auto-loads from the `.claude-plugin/` directory.

---

## Recommended Workflows

### The Easy Way: Use the Orchestrator

**Don't want to remember all the steps?** Just use `@feature-orchestrator`:

```
You: @feature-orchestrator I need to add a comments feature for blog posts
```

The orchestrator will:

1. Guide you through each stage
2. Run the right agents and commands
3. Checkpoint for your feedback
4. Not proceed until you're satisfied
5. Track progress and let you navigate back/forward

**Orchestrator Commands:**
| Command | Action |
|---------|--------|
| `continue` | Proceed to next stage |
| `back` | Return to previous stage |
| `skip` | Skip current stage |
| `adjust [feedback]` | Re-run with changes |
| `done` | Signal implementation complete |
| `status` | Show progress |

---

### Manual Workflow (Full Control)

If you prefer to run each step yourself:

```
1. @requirements-analyst    → Clarify what you're building
2. @api-designer           → Design the API contract
3. /fullstack:feature-new  → Scaffold all the code
4. [implement logic]       → Fill in business logic
5. @code-reviewer          → Review your implementation
6. @security-auditor       → Check for vulnerabilities
7. /check:all              → Run lints, types, tests
8. @docs-generator         → Generate documentation
```

**Example session:**

```
You: @requirements-analyst I need to add a comments feature to our app

[Agent asks clarifying questions, produces PRD]

You: @api-designer design the comments API based on those requirements

[Agent produces API specification]

You: /fullstack:feature-new comments

[Scaffolds backend + frontend code]

You: [implement the actual logic]

You: @code-reviewer review services/backend/app/services/comment_service.py

[Agent reviews and suggests improvements]

You: /check:all

[Runs all checks - fix any issues]

You: @docs-generator document the comments API
```

### Quick Backend Feature

When you only need backend changes:

```
/backend:feature-new [name]   → Full backend scaffold
# OR individual pieces:
/backend:model-new [name]     → Just the model
/backend:schema-new [name]    → Just schemas
/backend:service-new [name]   → Just the service
/backend:router-new [name]    → Just the router
```

### Quick Frontend Feature

When you only need frontend changes:

```
/frontend:feature-new [name]  → Full feature scaffold
# OR individual pieces:
/frontend:component-new [name] → Just a component
/frontend:hook-new [name]      → Just a hook
/frontend:page-new [name]      → Just a page
```

### Database Changes

```
/db:create "add comments table"  → Create migration
/db:migrate                      → Run migrations
/db:rollback                     → Undo last migration
/db:reset                        → Reset database (dev only!)
```

### Pre-Commit Checks

Always run before committing:

```
/check:all      → Everything (lint + types + tests)
# OR individually:
/check:lint     → ESLint only
/check:types    → TypeScript only
/check:tests    → Tests only
```

---

## Agent Best Practices

### @feature-orchestrator

**Best for:** Starting any new feature - it runs the entire workflow for you

**Tips for best results:**

- Describe your feature in plain language
- Answer checkpoint questions before proceeding
- Use `adjust` when something isn't quite right
- Don't skip security audit for auth-related features

**Good prompt:**

```
@feature-orchestrator I need to add a comments feature.
Users should be able to comment on posts, edit their comments,
and authors should be able to delete comments on their posts.
```

**What happens:**

1. Runs requirements analysis → checkpoints
2. Runs API design → checkpoints
3. Scaffolds code → checkpoints
4. Waits for your implementation
5. Reviews code → checkpoints
6. Security audit → checkpoints
7. Runs all checks → checkpoints
8. Generates docs → complete

---

### @requirements-analyst

**Best for:** Starting a new feature, unclear requirements

**Tips for best results:**

- Start vague, let the agent ask questions
- Answer the discovery questions thoroughly
- Ask for a PRD (Product Requirements Document) output
- Use the output as input for @api-designer

**Good prompt:**

```
@requirements-analyst I need to add a notifications system.
Users should be notified when someone comments on their posts.
```

**Output you'll get:**

- Clarifying questions
- User stories with acceptance criteria
- Edge cases identified
- PRD document

---

### @api-designer

**Best for:** Planning API endpoints before implementation

**Tips for best results:**

- Provide context about the feature
- Mention if it needs auth
- Specify if it's CRUD or has special operations

**Good prompt:**

```
@api-designer design REST API for a comments feature.
- Comments belong to posts and users
- Users can edit/delete their own comments
- Admins can delete any comment
- Support pagination and sorting
```

**Output you'll get:**

- Endpoint specifications
- Request/response schemas
- Error responses
- Auth requirements

---

### @code-reviewer

**Best for:** After completing code changes, before committing

**Tips for best results:**

- Point to specific files or directories
- Mention what kind of review you want
- Ask about specific concerns

**Good prompts:**

```
@code-reviewer review services/backend/app/services/comment_service.py

@code-reviewer check the new comments feature for CLAUDE.md pattern compliance

@code-reviewer are there any security issues in the new auth changes?
```

**Output you'll get:**

- Pattern violations
- Potential bugs
- Security concerns
- Suggested fixes with code

---

### @security-auditor

**Best for:** Before deployment, after auth/API changes

**Tips for best results:**

- Run on specific directories, not entire codebase
- Mention recent changes for context
- Ask about specific OWASP categories if concerned

**Good prompts:**

```
@security-auditor audit services/backend/app/routers/

@security-auditor check the file upload feature for security issues

@security-auditor review auth flow in services/backend/app/core/
```

**Output you'll get:**

- Vulnerabilities by severity (Critical/High/Medium/Low)
- OWASP/CWE references
- Remediation code snippets

---

### @performance-analyzer

**Best for:** When things are slow, before optimization

**Tips for best results:**

- Describe the performance issue
- Point to specific code paths
- Mention scale expectations

**Good prompts:**

```
@performance-analyzer the comments list is slow with many items

@performance-analyzer analyze database queries in user_service.py

@performance-analyzer check for N+1 queries in the posts feature
```

**Output you'll get:**

- Identified bottlenecks
- Before/after code comparisons
- Expected impact of fixes
- Profiling suggestions

---

### @pattern-enforcer

**Best for:** After generating code, during code review

**Tips for best results:**

- Point to files that should follow CLAUDE.md patterns
- Run after scaffolding commands
- Use when onboarding to verify understanding

**Good prompt:**

```
@pattern-enforcer check services/frontend/app/src/features/comments/ follows our patterns
```

**Output you'll get:**

- Compliance report
- Violations with specific fixes
- References to CLAUDE.md sections

---

### @refactoring-expert

**Best for:** When code is getting complex, before major changes

**Tips for best results:**

- Point to specific files or classes
- Mention what feels wrong
- Ask for metrics first, then suggestions

**Good prompts:**

```
@refactoring-expert this service is getting too big, help me split it

@refactoring-expert analyze complexity of services/backend/app/services/

@refactoring-expert the UserProfile component has too many responsibilities
```

**Output you'll get:**

- Complexity metrics
- Code smell identification
- Step-by-step refactoring plan
- Before/after comparisons

---

### @tech-stack-researcher

**Best for:** Evaluating new libraries, technology decisions

**Tips for best results:**

- Be specific about what you're trying to solve
- Mention alternatives you're considering
- Ask about compatibility with our stack

**Good prompts:**

```
@tech-stack-researcher should we use Zustand or Jotai for state management?

@tech-stack-researcher evaluate adding React Query to our frontend

@tech-stack-researcher what's the best approach for real-time updates in our stack?
```

**Output you'll get:**

- Compatibility analysis with our stack
- Alternative comparisons
- Recommendation with reasoning
- Integration notes

---

### @docs-generator

**Best for:** After completing features, generating API docs

**Tips for best results:**

- Point to specific code to document
- Specify the type of docs needed
- Mention the target audience

**Good prompts:**

```
@docs-generator create API documentation for the comments endpoints

@docs-generator add JSDoc to the useComments hook

@docs-generator write a README for the notifications feature
```

**Output you'll get:**

- Formatted documentation
- Working code examples
- API reference tables
- README sections

---

## Common Patterns

### Starting a Project Sprint

```bash
# 1. Review requirements
@requirements-analyst [feature description]

# 2. Design APIs
@api-designer [based on requirements]

# 3. Scaffold code
/fullstack:feature-new [name]

# 4. Implement
[your work here]

# 5. Review & ship
@code-reviewer [files]
@security-auditor [files]
/check:all
```

### Investigating Performance Issues

```bash
# 1. Identify bottlenecks
@performance-analyzer [describe issue]

# 2. Refactor if needed
@refactoring-expert [files]

# 3. Verify improvements
/check:tests
```

### Evaluating New Technology

```bash
# 1. Research
@tech-stack-researcher [technology question]

# 2. If adopting, check patterns
@pattern-enforcer [after integration]

# 3. Document
@docs-generator [new integration]
```

### Pre-Deployment Checklist

```bash
/check:all                    # All tests pass
@security-auditor [changes]   # No vulnerabilities
@pattern-enforcer [changes]   # Follows conventions
@docs-generator [new APIs]    # Documentation updated
```

---

## MCP Server Usage

### Context7 - Latest Documentation

Get up-to-date library docs:

```
"use context7 to look up React 19 Server Components"
"use context7 for FastAPI dependency injection patterns"
"use context7 to find Tailwind v4 migration guide"
```

### Neon - Database Management

Manage Neon PostgreSQL:

```
"show my Neon projects"
"create a new Neon branch called feature-comments"
"list databases in my Neon project"
```

### Redis Cloud - Cache Management

Manage Redis databases:

```
"list my Redis Cloud databases"
"create a new Redis database for caching"
"show Redis connection details"
```

---

## Tips for Best Results

### 1. Be Specific

```
# Bad
@code-reviewer review my code

# Good
@code-reviewer review services/backend/app/services/comment_service.py
for error handling and CLAUDE.md pattern compliance
```

### 2. Provide Context

```
# Bad
@security-auditor check security

# Good
@security-auditor audit the new file upload feature in
services/backend/app/routers/files.py - users can upload images up to 10MB
```

### 3. Chain Agents Logically

```
# Good workflow
@requirements-analyst → @api-designer → /fullstack:feature-new → @code-reviewer

# Not as effective
/fullstack:feature-new → @requirements-analyst (too late!)
```

### 4. Use Commands for Actions, Agents for Analysis

```
# Commands DO things
/fullstack:feature-new comments
/db:migrate
/check:all

# Agents ANALYZE things
@code-reviewer review...
@security-auditor audit...
@performance-analyzer check...
```

### 5. Iterate Based on Feedback

```
# Agent gives feedback → Fix issues → Re-run agent
@code-reviewer review X
[fix issues]
@code-reviewer review X again
```

---

## Troubleshooting

### Plugin Not Loading

- Ensure `.claude-plugin/plugin.json` exists
- Check you're in the project root directory
- Restart Claude Code

### MCP Server Not Working

- Verify environment variables are set
- Check MCP server is installed: `npx -y @package/name --version`
- Look for connection errors in Claude Code output

### Command Not Found

- Commands are case-sensitive
- Check exact syntax in PLUGIN.md
- Ensure you're using `/` prefix for commands, `@` for agents

### Agent Gives Generic Response

- Be more specific in your prompt
- Point to actual files/directories
- Provide more context about what you're trying to achieve
