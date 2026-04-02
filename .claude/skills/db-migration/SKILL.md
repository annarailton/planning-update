---
name: db-migration
description: Create or update database models and Alembic migrations. Auto-loads for schema changes, new tables, columns, enums, or model refactors.
disable-model-invocation: false
user-invocable: true
---

# Database Migration

Use this for schema-bearing database changes that need model edits and migrations.
If the request is only an API or service change without schema drift, another skill is a better fit.

## New Model

1. Create model:

```python
# packages/db/models/my_model.py
from sqlalchemy import String, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from packages.db.base import BaseModel
from uuid import UUID

class MyModel(BaseModel):
    __tablename__ = "my_models"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Foreign key
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))

    # Relationship
    user: Mapped["User"] = relationship(back_populates="my_models")
```

2. Export in `packages/db/__init__.py`:

```python
from packages.db.models.my_model import MyModel
```

3. Import in `packages/db/alembic/env.py`:

```python
from packages.db.models.my_model import MyModel  # Add import
```

4. Create migration: `pnpm db:create "add my_models table"`

5. Review generated migration -- verify column types, indexes, foreign keys

6. Run: `pnpm db:migrate`

## Modify Existing Model

1. Update model in `packages/db/models/`
2. `pnpm db:create "add field to my_model"`
3. Review generated migration
4. `pnpm db:migrate`

## Common Patterns

**Soft Delete (required):**

```python
is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
```

**Timestamps** -- inherited from BaseModel (`id`, `created_at`, `updated_at`)

**Enum Column:**

```python
from packages.db.constants import MyStatus  # Define in constants.py

status: Mapped[MyStatus] = mapped_column(default=MyStatus.PENDING)
```

**JSON Column:**

```python
from sqlalchemy import JSON

metadata: Mapped[dict] = mapped_column(JSON, default=dict)
```

## Rollback

```bash
# Last migration
docker compose exec backend alembic downgrade -1

# Specific revision
docker compose exec backend alembic downgrade <revision>
```

## Reset (Dev Only)

```bash
pnpm db:reset  # Drops all, recreates, runs migrations
```
