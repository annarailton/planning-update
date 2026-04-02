# API Endpoint Patterns

## Dependency Injection

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.auth import get_current_user

DatabaseDep = Annotated[AsyncSession, Depends(get_db)]
UserDep = Annotated[dict, Depends(get_current_user)]
ServiceDep = Annotated[MyService, Depends()]
```

## Pagination

```python
from fastapi import Query

@router.get("", response_model=ListResponse)
async def list_items(
    service: ServiceDep,
    db: DatabaseDep,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
):
    items, total = await service.list(db, limit, offset)
    return ListResponse(items=items, total=total)
```

## Error Responses

```python
from core.exceptions import NotFoundError, ConflictError, ValidationError

raise NotFoundError("Resource", id)    # 404
raise ConflictError("Already exists")  # 409
raise ValidationError("Invalid input") # 400
```

## Soft Delete

```python
async def delete(self, id: UUID, db: AsyncSession) -> Resource:
    resource = await self.get(id, db)
    resource.is_deleted = True
    await db.commit()
    return resource
```
