---
name: fullstack-feature
description: Create a coordinated backend and frontend feature. Auto-loads for work spanning API schemas, services, routers, plus frontend types, services, hooks, and UI.
disable-model-invocation: false
user-invocable: true
---

# Full-Stack Feature

Use this when one feature crosses backend and frontend boundaries and should land as a coordinated slice.
Prefer parallel implementation, but keep backend response shapes and frontend types aligned.
For frontend code, keep side effects in custom hooks and keep page/feature components focused on rendering.

```
Backend:                          Frontend:
├── schemas/feature.py            ├── features/feature/
├── services/feature_service.py   │   ├── components/
├── routers/feature.py            │   ├── hooks/
└── tests/test_feature.py         │   ├── services/
                                  │   ├── types/
                                  │   └── index.ts
```

## Parallel Implementation

Spawn multiple implementors:
1. Backend: Schema + Service + Router (use api-endpoint skill)
2. Frontend types: TypeScript types matching backend
3. Frontend service: API client functions
4. Frontend hooks: React hooks for data
5. Frontend UI: Components

## 1. Backend

```python
# Schema, Service, Router, Test
# Follow api-endpoint skill patterns
```

## 2. Frontend Types

```typescript
// features/my-feature/types/my-feature.types.ts
export interface MyResource {
  id: string;
  name: string;
  description: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface MyResourceCreate {
  name: string;
  description?: string;
}

export interface MyResourceUpdate {
  name?: string;
  description?: string;
}

export interface MyResourceListResponse {
  items: MyResource[];
  total: number;
}
```

## 3. Frontend Service

```typescript
// features/my-feature/services/myFeatureService.ts
import { apiClient } from "@/shared/lib/api-client";
import type {
  MyResource,
  MyResourceCreate,
  MyResourceUpdate,
  MyResourceListResponse,
} from "../types/my-feature.types";

export const myFeatureService = {
  create: (data: MyResourceCreate) =>
    apiClient.post<MyResource>("/my-resources", data),

  get: (id: string) => apiClient.get<MyResource>(`/my-resources/${id}`),

  list: (params?: { limit?: number; offset?: number }) =>
    apiClient.get<MyResourceListResponse>("/my-resources", { params }),

  update: (id: string, data: MyResourceUpdate) =>
    apiClient.put<MyResource>(`/my-resources/${id}`, data),

  delete: (id: string) => apiClient.delete(`/my-resources/${id}`),
};
```

## 4. Frontend Hooks

```typescript
// features/my-feature/hooks/useMyFeature.ts
import { useState, useEffect } from "react";
import { myFeatureService } from "../services/myFeatureService";
import type { MyResource } from "../types/my-feature.types";
import { logger } from "@/shared/lib/logger";

const log = logger.create("useMyFeature");

export function useMyFeature(id: string) {
  const [data, setData] = useState<MyResource | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function fetchData() {
      try {
        setLoading(true);
        const result = await myFeatureService.get(id, {
          signal: controller.signal,
        });
        setData(result);
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          log.error("Failed to fetch", err);
          setError(err);
        }
      } finally {
        setLoading(false);
      }
    }

    fetchData();
    return () => controller.abort();
  }, [id]);

  return { data, loading, error };
}

// features/my-feature/hooks/useMyFeatureList.ts
export function useMyFeatureList(limit = 20, offset = 0) {
  const [items, setItems] = useState<MyResource[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    myFeatureService
      .list({ limit, offset })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  }, [limit, offset]);

  return { items, total, loading, error };
}

// features/my-feature/hooks/useMyFeatureMutations.ts
export function useMyFeatureMutations() {
  const [loading, setLoading] = useState(false);

  const create = async (data: MyResourceCreate) => {
    setLoading(true);
    try {
      return await myFeatureService.create(data);
    } finally {
      setLoading(false);
    }
  };

  const update = async (id: string, data: MyResourceUpdate) => {
    setLoading(true);
    try {
      return await myFeatureService.update(id, data);
    } finally {
      setLoading(false);
    }
  };

  const remove = async (id: string) => {
    setLoading(true);
    try {
      await myFeatureService.delete(id);
    } finally {
      setLoading(false);
    }
  };

  return { create, update, remove, loading };
}
```

## 5. Frontend Components

```typescript
// features/my-feature/components/MyFeatureList.tsx
import { useMyFeatureList } from '../hooks/useMyFeatureList';
import { MyFeatureCard } from './MyFeatureCard';

export function MyFeatureList() {
  const { items, total, loading } = useMyFeatureList();

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <p>{total} items</p>
      {items.map(item => (
        <MyFeatureCard key={item.id} item={item} />
      ))}
    </div>
  );
}
```

Component rule:
- Do not introduce `useEffect` in page/feature components for data or orchestration logic
- Put those effects into `features/*/hooks` or `shared/hooks` and consume hook outputs in components

## 6. Export

```typescript
// features/my-feature/index.ts
export * from "./components/MyFeatureList";
export * from "./components/MyFeatureCard";
export * from "./hooks/useMyFeature";
export * from "./hooks/useMyFeatureList";
export * from "./hooks/useMyFeatureMutations";
export * from "./types/my-feature.types";
```

## Verify

- Backend schema matches frontend types
- API endpoints return expected format
- Error handling in hooks
- Loading states in components
- No data/orchestration `useEffect` inside page/feature components
- AbortController for cleanup
- Logger instead of console.log
