# Frontend Service

React 19 + TypeScript + Vite, deployed to Cloud Run (Nginx).

## Structure

```
app/src/
  features/   # Domain modules (auth, files, chat)
  shared/     # Cross-cutting (components, hooks, lib)
  pages/      # Route components (thin)
```

```
features/{name}/
  components/    # UserCard.tsx, UserList.tsx
  hooks/         # useUsers.ts, useUserMutations.ts
  services/      # userService.ts
  types/         # user.types.ts
  index.ts       # Public exports
```

## Required Imports

| WRONG                           | RIGHT                                                 |
| ------------------------------- | ----------------------------------------------------- |
| `import.meta.env.VITE_*`        | `import { config } from '@/shared/lib/config'`        |
| `console.log` / `console.error` | `import { logger } from '@/shared/lib/logger'`        |
| `fetch("/api/...")`             | `import { apiClient } from '@/shared/lib/api-client'` |
| `any`                           | Define a typed interface                              |

## Patterns

### Service

```typescript
import { apiClient } from "@/shared/lib/api-client";

export const userService = {
  getAll: () => apiClient.get<User[]>("/users"),
  create: (data: CreateUser) => apiClient.post<User>("/users", data),
};
```

### Hook

```typescript
export function useUsers() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    userService
      .getAll()
      .then(setUsers)
      .finally(() => setLoading(false));
  }, []);

  return { users, loading };
}
```

### Component Boundary

- Page/feature components should consume hooks and render UI
- Avoid `useEffect` directly in page/feature components
- Put data-fetching, subscriptions, and orchestration side effects in `features/*/hooks` or `shared/hooks`
- Exception: component-local UI effects are allowed when no reusable hook makes sense (for example focus trap, element measurement, animation lifecycle)

Bad (effect in component):

```typescript
export function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  useEffect(() => {
    userService.getAll().then(setUsers);
  }, []);
  return <UserList users={users} />;
}
```

Good (effect in hook):

```typescript
export function UsersPage() {
  const { users } = useUsers();
  return <UserList users={users} />;
}
```

### Feature Flags

```typescript
import { useFeatures } from "@/shared/hooks/useFeatures";

const { isRedisEnabled, isTemporalEnabled } = useFeatures();
```

### Logger

```typescript
const log = logger.create("UserList");
log.debug("Fetching users"); // Dev only
log.error("Failed", err); // Always shown
```

## Conventions

| Category   | Rule                                                                          |
| ---------- | ----------------------------------------------------------------------------- |
| Components | `PascalCase.tsx`, props interface above component                             |
| Hooks      | `use*.ts`, extract logic from components, return named object, own `useEffect` side effects |
| Services   | `camelCase.ts`, all API calls through `apiClient`                             |
| Types      | `PascalCase` interfaces, export from `types/` files                           |
| UI         | shadcn/ui (`shared/components/ui/`), Tailwind, Motion (`from 'motion/react'`) |

## Tests

```bash
pnpm test:frontend
```

## Adding Features

1. Create `features/{name}/` structure
2. Define types in `types/`
3. API calls in `services/`
4. Logic in `hooks/`
5. UI in `components/`
6. Export public API in `index.ts`
