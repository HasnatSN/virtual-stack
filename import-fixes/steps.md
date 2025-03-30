# Import Path Standardization Steps

## Overview

We're facing inconsistent import paths in the codebase. Some files use `virtualstack`, others use `src.virtualstack`. We need to standardize on one approach for the entire project.

## Decision

We will standardize on using **relative imports** throughout the project, as this is the most reliable approach for our project structure. This means:

1. From files in the `src/virtualstack` directory, we'll use `from virtualstack...` for imports
2. We won't use `src.virtualstack` anywhere in the code
3. We'll adjust the PYTHONPATH when running the application so that imports work correctly

## Step-by-step Plan

### Step 1: Fix main.py

Update `src/virtualstack/main.py` to use relative imports:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from virtualstack.core.config import settings
from virtualstack.api.v1.api import api_router
from virtualstack.api.middleware import setup_middleware

# Rest of the file remains the same
```

### Step 2: Fix api.py

Update `src/virtualstack/api/v1/api.py` to use relative imports:

```python
from fastapi import APIRouter

from virtualstack.api.v1.endpoints import auth, users, tenants, api_keys

# Rest of the file remains the same
```

### Step 3: Fix endpoints

Update all endpoint files to use relative imports:

- `src/virtualstack/api/v1/endpoints/auth.py`
- `src/virtualstack/api/v1/endpoints/users.py`
- `src/virtualstack/api/v1/endpoints/tenants.py`
- `src/virtualstack/api/v1/endpoints/api_keys.py`

### Step 4: Fix core modules

Update all core modules to use relative imports:

- `src/virtualstack/core/security.py`
- `src/virtualstack/db/session.py`

### Step 5: Fix schemas imports

Check if there are any import issues in:

- `src/virtualstack/schemas/__init__.py`

### Step 6: Fix service modules

Check any service modules for inconsistent imports:

- `src/virtualstack/services/iam/api_key.py`

### Step 7: Run with correct PYTHONPATH

To run the application, use:

```bash
cd src
python3 -m uvicorn virtualstack.main:app
```

Or if you need to run from the project root:

```bash
PYTHONPATH=$PYTHONPATH:$(pwd)/src python3 -m uvicorn virtualstack.main:app
```

## Testing After Each Step

After fixing imports in each file, run:

```bash
cd src
python3 -c "import virtualstack.FILE_PATH_TO_TEST"
```

For example:
```bash
cd src
python3 -c "import virtualstack.main"
```

This will help identify any remaining import errors. 