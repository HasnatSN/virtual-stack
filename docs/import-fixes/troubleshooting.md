# Troubleshooting Common Import Errors

This guide helps you diagnose and fix common import-related errors in the VirtualStack project.

## ModuleNotFoundError: No module named 'src'

### Symptoms
```
Traceback (most recent call last):
  File "/path/to/app/main.py", line 3, in <module>
    from src.virtualstack.core.config import settings
ModuleNotFoundError: No module named 'src'
```

### Cause
You're using imports that include `src.virtualstack`, but Python doesn't recognize `src` as a module because:
- You're running from inside the `src` directory
- Or the `src` directory isn't in your PYTHONPATH

### Solution
1. Change imports from `from src.virtualstack.X import Y` to `from virtualstack.X import Y`
2. Run the application from the `src` directory: `cd src && python -m uvicorn virtualstack.main:app`

## ImportError: attempted relative import with no known parent package

### Symptoms
```
Traceback (most recent call last):
  File "/path/to/app/main.py", line 5, in <module>
    from .core.config import settings
ImportError: attempted relative import with no known parent package
```

### Cause
You're using relative imports (starting with `.`) but running the file directly instead of as a module.

### Solution
Run the file as a module:
```bash
python -m virtualstack.main
```
Instead of:
```bash
python virtualstack/main.py
```

## Circular Import Errors

### Symptoms
```
Traceback (most recent call last):
  File "/path/to/app/main.py", line 3, in <module>
    from virtualstack.api.v1.api import api_router
  File "/path/to/app/api/v1/api.py", line 2, in <module>
    from virtualstack.api.v1.endpoints.users import router as users_router
  File "/path/to/app/api/v1/endpoints/users.py", line 5, in <module>
    from virtualstack.main import app
ImportError: cannot import name 'app' from 'virtualstack.main'
```

### Cause
You have a circular dependency where module A imports from module B, which imports from module A.

### Solution
1. Restructure your imports to break the circular dependency
2. Move the import statement inside the function where it's needed
3. Use lazy imports:
   ```python
   def get_app():
       from virtualstack.main import app
       return app
   ```

## Package Not Found Despite Being Installed

### Symptoms
```
ModuleNotFoundError: No module named 'fastapi'
```
(But you know you've installed FastAPI)

### Cause
You may be using a different Python environment than the one where you installed the package.

### Solution
1. Verify which Python is being used: `which python3`
2. Install the package for the current Python: `pip3 install fastapi`
3. Consider using a virtual environment: `python -m venv venv && source venv/bin/activate`

## Testing Your Import Structure

To verify your import structure works correctly:

```python
# Create a test.py file
import sys
print(sys.path)  # See where Python is looking for imports

try:
    import virtualstack
    print("✅ virtualstack module can be imported")
except ImportError as e:
    print(f"❌ Error importing virtualstack: {e}")

try:
    from virtualstack.core.config import settings
    print("✅ settings can be imported")
except ImportError as e:
    print(f"❌ Error importing settings: {e}")
```

Run it with:
```bash
cd /path/to/project/root
PYTHONPATH=src python test.py
``` 