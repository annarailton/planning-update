---
paths:
  - "**/tests/**"
  - "**/test_*.py"
  - "**/*.test.ts"
  - "**/*.test.tsx"
  - "**/conftest.py"
---

# Testing Rules

## Verification Before Done

- Never mark a task complete without evidence it works.
- Mandatory gate: run `/clean-slop` before marking any task done, fix all findings, and re-run until no findings remain.
- Use the lightest proof that matches risk and scope.
- Prefer walkthroughs/integration checks for user-facing flows.
- Use targeted tests when walkthrough evidence is weak or missing.
- For config/docs/sync changes, use consistency checks (for example `/sync-configs`) instead of new tests.

## Execution Protocol (LLM)

- Plan before implementation for non-trivial tasks (`>=3` steps, multi-service changes, or architecture/config-sync decisions).
- Re-plan immediately if first pass introduces drift/regression, scope changes materially, or the same verification fails twice.
- Keep changes minimal: touch only necessary files; avoid speculative refactors.
- Follow phases sequentially — never skip or jump ahead unless told.
- Verify stubs are wired up before marking phase complete.
- Simplest approach first — no speculative abstractions.

## Commands

```bash
pnpm test:backend     # Backend pytest
pnpm test:frontend    # Frontend vitest
```

## Backend (pytest)

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

## Frontend (vitest)

- React Testing Library for components
- Mock API calls with MSW or vi.mock
- Test user interactions, not implementation

```typescript
test('shows user name', async () => {
  render(<UserCard user={mockUser} />);
  expect(screen.getByText(mockUser.name)).toBeInTheDocument();
});
```
