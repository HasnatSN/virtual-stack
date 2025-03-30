# Step 1: Fix main.py

## Current Issue

In `src/virtualstack/main.py`, the imports are using the `src.virtualstack` prefix, which causes import errors when running the application from the `src` directory.

## Current Code

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.virtualstack.core.config import settings
from src.virtualstack.api.v1.api import api_router
from src.virtualstack.api.middleware import setup_middleware

# ... rest of the file
```

## Fixed Code

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from virtualstack.core.config import settings
from virtualstack.api.v1.api import api_router
from virtualstack.api.middleware import setup_middleware

# ... rest of the file
```

## Steps to Fix

1. Edit `src/virtualstack/main.py`
2. Replace all instances of `from src.virtualstack.` with `from virtualstack.`
3. Save the file

## Verify

After making the changes, test if the imports work correctly by running:

```bash
cd src
python3 -c "import virtualstack.main"
```

If there are no errors, proceed to the next step. 