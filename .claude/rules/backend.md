---
paths:
  - "services/backend/**"
  - "packages/**/*.py"
---

# Backend Rules

## Imports

- `from core.config import get_settings` not `os.getenv()`
- `from core.exceptions import NotFoundError` not `HTTPException`
- `from packages.db import User` for models

## Patterns

- Business logic in `services/`, not `routers/`
- Use `Annotated[Type, Depends()]` for DI
- SQLAlchemy 2.0: `select()` not `query()`
- All DB calls async with `await`
- Soft delete: `is_deleted` flag

## Error Handling

```python
raise NotFoundError("User", id)     # 404
raise ConflictError("Exists")       # 409
raise ValidationError("Invalid")    # 400
```

## Testing

- Fixtures in `conftest.py`
- Mock external services
- Test both success and error paths
