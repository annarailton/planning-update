# Backend Service

FastAPI + async SQLAlchemy, deployed to Cloud Run.

## Structure

```
app/
  core/       # Config, auth, exceptions
  routers/    # HTTP endpoints (thin)
  services/   # Business logic
  schemas/    # Pydantic models
  tests/      # pytest
```

## Rules

| WRONG                      | RIGHT                                  | Why                      |
| -------------------------- | -------------------------------------- | ------------------------ |
| `os.getenv("KEY")`         | `from core.config import get_settings` | Type-safe Settings class |
| `raise HTTPException(404)` | `raise NotFoundError("User", id)`      | Domain exceptions        |
| `db.query(User)`           | `select(User).where(...)`              | SQLAlchemy 2.0           |
| Logic in router            | Logic in `services/`                   | Thin routers             |
| `hard_delete(user)`        | `user.is_deleted = True`               | Soft delete only         |
| Sync DB calls              | `await db.execute(stmt)`               | Async everything         |

- DI via `Annotated[UserService, Depends()]` (aliased as `UserServiceDep`)
- Models: `from packages.db import User`
- Exceptions: `NotFoundError` (404), `ConflictError` (409), `ValidationError` (400)

## Patterns

### Router -> Service

```python
@router.post("/users")
async def create_user(
    data: UserCreate,
    service: UserServiceDep,  # Annotated[UserService, Depends()]
    db: DatabaseDep
):
    return await service.create(data, db)
```

### Service Layer

```python
class UserService:
    async def create(self, data: UserCreate, db: AsyncSession) -> User:
        if await self._exists(data.email, db):
            raise ConflictError("Email exists")
        user = User(**data.model_dump())
        db.add(user)
        await db.commit()
        return user
```

### SQLAlchemy 2.0 Queries

```python
stmt = select(User).where(User.email == email, User.is_deleted == False)
result = await db.execute(stmt)
user = result.scalar_one_or_none()
```

## LLM Usage

```python
# Direct package
import packages.openai as openai
response = await openai.chat([{"role": "user", "content": "Hi"}])

# Via service (with tracing)
from services.llm import LLMService
response = await llm.chat(messages=[...], provider="anthropic")
```

## Tests

```bash
pnpm test:backend           # All tests
docker compose exec backend pytest app/tests/test_users.py -v
```

- Fixtures in `conftest.py`; mock external services; test success + error paths

## Adding Endpoints

1. Schema in `schemas/`
2. Service in `services/`
3. Router in `routers/` (thin)
4. Register in `routers/__init__.py`
5. Test in `tests/`
