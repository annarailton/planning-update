---
name: api-endpoint
description: Create a backend API endpoint with schema, service, router, and test. Auto-loads for REST endpoints, CRUD routes, or backend API work.
disable-model-invocation: false
user-invocable: true
---

# API Endpoint

Build the standard backend slice for one endpoint family: schema, service, router, and test.
Auto-load this for new REST resources or route additions, not for frontend-only work or database-only changes.

```
services/backend/app/
├── schemas/my_resource.py    # Request/response models
├── services/my_service.py    # Business logic
├── routers/my_resource.py    # HTTP endpoints
└── tests/test_my_resource.py # Tests
```

## 1. Schema

```python
# services/backend/app/schemas/my_resource.py
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

## 2. Service

```python
# services/backend/app/services/my_service.py
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from packages.db import MyResource
from core.exceptions import NotFoundError, ConflictError
from schemas.my_resource import MyResourceCreate, MyResourceUpdate

class MyResourceService:
    async def create(
        self, data: MyResourceCreate, db: AsyncSession
    ) -> MyResource:
        resource = MyResource(**data.model_dump())
        db.add(resource)
        await db.commit()
        await db.refresh(resource)
        return resource

    async def get(self, id: UUID, db: AsyncSession) -> MyResource:
        stmt = select(MyResource).where(
            MyResource.id == id,
            MyResource.is_deleted == False
        )
        result = await db.execute(stmt)
        resource = result.scalar_one_or_none()
        if not resource:
            raise NotFoundError("MyResource", id)
        return resource

    async def list(
        self, db: AsyncSession, limit: int = 20, offset: int = 0
    ) -> tuple[list[MyResource], int]:
        # Count
        count_stmt = select(func.count()).where(MyResource.is_deleted == False)
        total = (await db.execute(count_stmt)).scalar()

        # Items
        stmt = (
            select(MyResource)
            .where(MyResource.is_deleted == False)
            .limit(limit)
            .offset(offset)
            .order_by(MyResource.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def update(
        self, id: UUID, data: MyResourceUpdate, db: AsyncSession
    ) -> MyResource:
        resource = await self.get(id, db)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(resource, key, value)
        await db.commit()
        await db.refresh(resource)
        return resource

    async def delete(self, id: UUID, db: AsyncSession) -> MyResource:
        resource = await self.get(id, db)
        resource.is_deleted = True
        await db.commit()
        return resource
```

## 3. Router

```python
# services/backend/app/routers/my_resource.py
from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.auth import get_current_user
from services.my_service import MyResourceService
from schemas.my_resource import (
    MyResourceCreate, MyResourceUpdate,
    MyResourceResponse, MyResourceListResponse
)

router = APIRouter(prefix="/my-resources", tags=["my-resources"])

# Dependencies
DatabaseDep = Annotated[AsyncSession, Depends(get_db)]
ServiceDep = Annotated[MyResourceService, Depends()]
UserDep = Annotated[dict, Depends(get_current_user)]

@router.post("", response_model=MyResourceResponse, status_code=201)
async def create(
    data: MyResourceCreate,
    service: ServiceDep,
    db: DatabaseDep,
    user: UserDep,
):
    return await service.create(data, db)

@router.get("/{id}", response_model=MyResourceResponse)
async def get(id: UUID, service: ServiceDep, db: DatabaseDep, user: UserDep):
    return await service.get(id, db)

@router.get("", response_model=MyResourceListResponse)
async def list(
    service: ServiceDep,
    db: DatabaseDep,
    user: UserDep,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
):
    items, total = await service.list(db, limit, offset)
    return MyResourceListResponse(items=items, total=total)

@router.put("/{id}", response_model=MyResourceResponse)
async def update(
    id: UUID,
    data: MyResourceUpdate,
    service: ServiceDep,
    db: DatabaseDep,
    user: UserDep,
):
    return await service.update(id, data, db)

@router.delete("/{id}", status_code=204)
async def delete(id: UUID, service: ServiceDep, db: DatabaseDep, user: UserDep):
    await service.delete(id, db)
```

## 4. Register Router

```python
# services/backend/app/routers/__init__.py
from routers.my_resource import router as my_resource_router

routers = [
    # ... existing routers
    my_resource_router,
]
```

## 5. Test

```python
# services/backend/app/tests/test_my_resource.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_my_resource(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/my-resources",
        json={"name": "Test Resource"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Resource"

@pytest.mark.asyncio
async def test_get_my_resource_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.get(
        "/api/my-resources/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert response.status_code == 404
```
