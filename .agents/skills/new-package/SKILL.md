---
name: new-package
description: Create a shared Python package under packages/. Use for reusable clients, integrations, helpers, or code shared across services.
---

# New Shared Package

Use this when code should live in `packages/` and be reused across services.
Do not use this for app-local helpers that belong inside a single service.

```
packages/my_package/
├── __init__.py          # Public API exports
├── client.py            # Main functionality
├── types.py             # Type definitions
├── exceptions.py        # Package-specific exceptions (optional)
└── pyproject.toml       # Package metadata
```

## 1. Create Directory

```bash
mkdir -p packages/my_package
```

## 2. pyproject.toml

```toml
# packages/my_package/pyproject.toml
[project]
name = "my_package"
version = "0.1.0"
description = "Description of what this package does"
requires-python = ">=3.12"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## 3. __init__.py

```python
# packages/my_package/__init__.py
"""
My Package - Brief description.

Usage:
    from packages.my_package import MyClient, MyType

    client = MyClient()
    result = await client.do_something()
"""

from packages.my_package.client import MyClient
from packages.my_package.types import MyType, MyConfig

__all__ = ["MyClient", "MyType", "MyConfig"]
```

## 4. Types

```python
# packages/my_package/types.py
from dataclasses import dataclass
from enum import Enum

class MyStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"

@dataclass
class MyConfig:
    api_key: str
    timeout: int = 30

@dataclass
class MyType:
    id: str
    status: MyStatus
    data: dict
```

## 5. Client

```python
# packages/my_package/client.py
from packages.my_package.types import MyConfig, MyType

class MyClient:
    def __init__(self, config: MyConfig | None = None):
        self.config = config or MyConfig(api_key="")
        self._client = None

    async def do_something(self, input: str) -> MyType:
        """Do something and return result."""
        # Implementation
        return MyType(id="123", status=MyStatus.COMPLETED, data={})

    async def close(self):
        """Cleanup resources."""
        if self._client:
            await self._client.close()
```

## 6. Use in Services

```python
# services/backend/app/services/my_service.py
from packages.my_package import MyClient, MyConfig

client = MyClient(MyConfig(api_key=settings.my_api_key))
```

## Common Patterns

**Singleton Client:**

```python
_client: MyClient | None = None

def get_client() -> MyClient:
    global _client
    if _client is None:
        _client = MyClient()
    return _client
```

**Feature Flag Check:**

```python
def is_enabled() -> bool:
    from core.config import get_settings
    settings = get_settings()
    return bool(settings.my_package_api_key)
```

**Custom Exception:**

```python
from packages.exceptions import ExternalAPIError

class MyPackageError(ExternalAPIError):
    pass
```
