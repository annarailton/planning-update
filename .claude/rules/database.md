---
paths:
  - "packages/db/**"
  - "**/migrations/**"
  - "**/alembic/**"
---

# Database Rules

## Models

- Inherit from `BaseModel` (includes id, created_at, updated_at)
- Add `is_deleted` for soft delete
- Define relationships explicitly

```python
class User(BaseModel):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(255), unique=True)
    is_deleted: Mapped[bool] = mapped_column(default=False)
```

## Migrations

1. Create: `pnpm db:create "description"`
2. Run: `pnpm db:migrate`
3. Reset: `pnpm db:reset`

## Queries

```python
# Always SQLAlchemy 2.0 style
stmt = select(User).where(User.email == email, User.is_deleted == False)
result = await db.execute(stmt)
user = result.scalar_one_or_none()
```

## Constants

Define enums in `packages/db/constants.py` to prevent drift across services.
