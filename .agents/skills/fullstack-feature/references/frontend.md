# Frontend Reference

## Types Template

```typescript
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

export interface MyResourceListResponse {
  items: MyResource[];
  total: number;
}
```

## Service Template

```typescript
import { apiClient } from "@/shared/lib/api-client";
import type {
  MyResource,
  MyResourceCreate,
  MyResourceListResponse,
} from "../types/my-feature.types";

export const myFeatureService = {
  create: (data: MyResourceCreate) =>
    apiClient.post<MyResource>("/my-resources", data),
  get: (id: string) => apiClient.get<MyResource>(`/my-resources/${id}`),
  list: (params?: { limit?: number; offset?: number }) =>
    apiClient.get<MyResourceListResponse>("/my-resources", { params }),
  delete: (id: string) => apiClient.delete(`/my-resources/${id}`),
};
```

## Hook Template

```typescript
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
        const result = await myFeatureService.get(id);
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
```

## Component Template

```typescript
import { useMyFeatureList } from '../hooks/useMyFeatureList';

export function MyFeatureList() {
  const { items, total, loading } = useMyFeatureList();
  if (loading) return <div>Loading...</div>;
  return (
    <div>
      <p>{total} items</p>
      {items.map(item => <MyFeatureCard key={item.id} item={item} />)}
    </div>
  );
}
```

## Export Template

```typescript
// features/my-feature/index.ts
export * from "./components/MyFeatureList";
export * from "./hooks/useMyFeature";
export * from "./hooks/useMyFeatureList";
export * from "./types/my-feature.types";
```
