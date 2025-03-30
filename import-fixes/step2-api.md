# Step 2: Fix api.py

## Current Issue

In `src/virtualstack/api/v1/api.py`, the imports are using the `src.virtualstack` prefix, which causes import errors when running the application from the `src` directory.

## Current Code

```python
from fastapi import APIRouter

from src.virtualstack.api.v1.endpoints import auth, users, tenants, api_keys

api_router = APIRouter()

# ... rest of the file
```

## Fixed Code

```python
from fastapi import APIRouter

from virtualstack.api.v1.endpoints import auth, users, tenants, api_keys

api_router = APIRouter()

# ... rest of the file
```

## Steps to Fix

1. Edit `src/virtualstack/api/v1/api.py`
2. Replace all instances of `from src.virtualstack.` with `from virtualstack.`
3. Save the file

## Verify

After making the changes, test if the imports work correctly by running:

```bash
cd src
python3 -c "import virtualstack.api.v1.api"
```

If there are no errors, proceed to the next step. 