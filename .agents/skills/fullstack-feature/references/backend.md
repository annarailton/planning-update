# Backend Reference

## Schema Template

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class MyResourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None

class MyResourceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None

class MyResourceResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class MyResourceListResponse(BaseModel):
    items: list[MyResourceResponse]
    total: int
```

## Service Template

```python
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from packages.db import MyResource
from core.exceptions import NotFoundError
from schemas.my_resource import MyResourceCreate, MyResourceUpdate

class MyResourceService:
    async def create(self, data: MyResourceCreate, db: AsyncSession) -> MyResource:
        resource = MyResource(**data.model_dump())
        db.add(resource)
        await db.commit()
        await db.refresh(resource)
        return resource

    async def get(self, id: UUID, db: AsyncSession) -> MyResource:
        stmt = select(MyResource).where(MyResource.id == id, MyResource.is_deleted == False)
        result = await db.execute(stmt)
        resource = result.scalar_one_or_none()
        if not resource:
            raise NotFoundError("MyResource", id)
        return resource

    async def delete(self, id: UUID, db: AsyncSession) -> MyResource:
        resource = await self.get(id, db)
        resource.is_deleted = True
        await db.commit()
        return resource
```
