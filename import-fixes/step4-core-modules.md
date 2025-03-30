# Step 4: Fix Core Modules

## Current Issue

In the core modules, the imports are using the `src.virtualstack` prefix, which causes import errors when running the application from the `src` directory.

## Files to Fix

We need to update the following files:

1. `src/virtualstack/core/security.py`
2. `src/virtualstack/db/session.py`

## Fix for security.py

### Current Code

```python
from datetime import datetime, timedelta
from typing import Any, Optional, Union

from jose import jwt
from passlib.context import CryptContext

from src.virtualstack.core.config import settings

# ... rest of the file
```

### Fixed Code

```python
from datetime import datetime, timedelta
from typing import Any, Optional, Union

from jose import jwt
from passlib.context import CryptContext

from virtualstack.core.config import settings

# ... rest of the file
```

## Fix for session.py

### Current Code

```python
from typing import Generator, Any, Dict, Optional, List
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker

from src.virtualstack.core.config import settings

# ... rest of the file
```

### Fixed Code

```python
from typing import Generator, Any, Dict, Optional, List
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker

from virtualstack.core.config import settings

# ... rest of the file
```

## Steps to Fix

1. Edit each file
2. Replace all instances of `from src.virtualstack.` with `from virtualstack.`
3. Save the file

## Verify

After making the changes to each file, test if the imports work correctly by running:

```bash
cd src
python3 -c "import virtualstack.core.security"
python3 -c "import virtualstack.db.session"
```

If there are no errors, proceed to the next step. 