# Step 3: Fix Endpoint Files

## Current Issue

In the endpoint files under `src/virtualstack/api/v1/endpoints/`, the imports are using the `src.virtualstack` prefix, which causes import errors when running the application from the `src` directory.

## Files to Fix

We need to update the following files:

1. `src/virtualstack/api/v1/endpoints/auth.py`
2. `src/virtualstack/api/v1/endpoints/users.py`
3. `src/virtualstack/api/v1/endpoints/tenants.py`
4. `src/virtualstack/api/v1/endpoints/api_keys.py`

## Fix for auth.py

### Current Code

```python
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.virtualstack.core.config import settings
from src.virtualstack.core.exceptions import http_authentication_error
from src.virtualstack.core.security import create_access_token
from src.virtualstack.core.rate_limiter import rate_limit
from src.virtualstack.db.session import get_db
from src.virtualstack.schemas.iam.auth import Token, LoginRequest
from src.virtualstack.services.iam import user_service

# ... rest of the file
```

### Fixed Code

```python
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.core.config import settings
from virtualstack.core.exceptions import http_authentication_error
from virtualstack.core.security import create_access_token
from virtualstack.core.rate_limiter import rate_limit
from virtualstack.db.session import get_db
from virtualstack.schemas.iam.auth import Token, LoginRequest
from virtualstack.services.iam import user_service

# ... rest of the file
```

## Fix for users.py, tenants.py, and api_keys.py

Apply the same pattern to these files:

1. Edit each file
2. Replace all instances of `from src.virtualstack.` with `from virtualstack.`
3. Save the file

## Verify

After making the changes to each file, test if the imports work correctly by running:

```bash
cd src
python3 -c "import virtualstack.api.v1.endpoints.auth"
python3 -c "import virtualstack.api.v1.endpoints.users"
python3 -c "import virtualstack.api.v1.endpoints.tenants"
python3 -c "import virtualstack.api.v1.endpoints.api_keys"
```

If there are no errors, proceed to the next step. 