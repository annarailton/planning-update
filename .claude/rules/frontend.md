---
paths:
  - "services/frontend/**"
---

# Frontend Rules

## Imports

- `import { config } from '@/shared/lib/config'` not `import.meta.env`
- `import { logger } from '@/shared/lib/logger'` not `console.log`
- `import { apiClient } from '@/shared/lib/api-client'` for API calls

## Structure

- Features in `features/{domain}/` with components, hooks, services, types
- Shared utilities in `shared/`
- Thin route components in `pages/`

## TypeScript

- No `any` types - define interfaces
- Export types from `types/` files
- Use `PascalCase` for interfaces

## Hooks

- Prefix with `use`
- Extract logic from components
- Return object with named values
- Keep `useEffect` in custom hooks, not in page/feature components
- Exception: component-local UI effects are allowed when no reusable hook makes sense (for example focus trap, element measurement, animation lifecycle)

Bad:

```typescript
export function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  useEffect(() => {
    userService.getAll().then(setUsers);
  }, []);
  return <UserList users={users} />;
}
```

Good:

```typescript
export function UsersPage() {
  const { users } = useUsers();
  return <UserList users={users} />;
}
```

## Components

- `PascalCase.tsx` naming
- Props interface above component
- Use shadcn/ui from `shared/components/ui/`
