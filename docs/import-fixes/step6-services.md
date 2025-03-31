# Step 6: Fix Service Modules

## Current Issue

The service modules might have inconsistent import paths, which can cause import errors when running the application.

## Files to Check and Fix

We need to check and update the following files:

1. `src/virtualstack/services/iam/api_key.py` 
2. `src/virtualstack/services/iam/__init__.py`
3. Any other service files that might have inconsistent imports

## Fix for api_key.py

Check the current content of the file:

```bash
head -n 20 src/virtualstack/services/iam/api_key.py
```

If it contains imports using `src.virtualstack`, we need to fix them:

### Example Fix

If the file contains:

```python
from src.virtualstack.models.iam.api_key import APIKey
from src.virtualstack.schemas.iam.api_key import APIKeyCreate, APIKeyUpdate
```

Change it to:

```python
from virtualstack.models.iam.api_key import APIKey
from virtualstack.schemas.iam.api_key import APIKeyCreate, APIKeyUpdate
```

## Fix for services/iam/__init__.py

Check the current content:

```bash
cat src/virtualstack/services/iam/__init__.py
```

Apply the same pattern to fix any absolute imports with relative imports.

## Verify

After making the changes, test if the imports work correctly by running:

```bash
cd src
python3 -c "import virtualstack.services.iam.api_key"
```

If there are no errors, proceed to the next step. 