# Step 5: Fix Schema Imports

## Current Issue

The error logs show that there might be import issues in the schemas files, particularly in `src/virtualstack/schemas/__init__.py`.

## Check and Fix schemas/__init__.py

First, let's check the current content of this file:

```bash
cat src/virtualstack/schemas/__init__.py
```

If it contains imports using `virtualstack.schemas` instead of relative imports, we need to fix it.

### Example Fix

If the file contains:

```python
from virtualstack.schemas.iam import *
```

Change it to:

```python
from .iam import *
```

If the file contains:

```python
from src.virtualstack.schemas.iam import *
```

Change it to:

```python
from .iam import *
```

## Check and Fix schemas/iam/__init__.py

Also check the imports in `src/virtualstack/schemas/iam/__init__.py`:

```bash
cat src/virtualstack/schemas/iam/__init__.py
```

Apply the same pattern to fix any absolute imports with relative ones.

## Verify

After making the changes, test if the imports work correctly by running:

```bash
cd src
python3 -c "import virtualstack.schemas"
```

If there are no errors, proceed to the next step. 