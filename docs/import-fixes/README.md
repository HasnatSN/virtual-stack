# Import Path Standardization Guide

This guide provides step-by-step instructions for fixing import path inconsistencies in the VirtualStack backend project.

## Background

The project has inconsistent import paths:
- Some files use `virtualstack.` prefix
- Others use `src.virtualstack.` prefix

These inconsistencies cause "ModuleNotFoundError" errors when running the application.

## The Solution

We've standardized on using the `virtualstack.` prefix for imports when running from inside the `src` directory.

## Automated Fix

For those who prefer an automated solution, we've provided:

1. [Python script to fix imports](./fix_imports.py) - Automatically fixes all import issues
   ```bash
   # Run from project root in dry-run mode first
   python import-fixes/fix_imports.py --dry-run
   
   # Then run it for real
   python import-fixes/fix_imports.py
   ```

2. [Quick shell command](./quick-fix.md) - Single shell command to fix all imports

## Step-by-Step Manual Fix

For those who want to understand and fix each file individually:

1. [Fix main.py](./step1-main.md) - Update the FastAPI application entry point
2. [Fix api.py](./step2-api.md) - Update the API router imports
3. [Fix endpoint files](./step3-endpoints.md) - Update auth, users, tenants, and api_keys endpoints
4. [Fix core modules](./step4-core-modules.md) - Update security.py and session.py
5. [Fix schema imports](./step5-schemas.md) - Update schema-related imports
6. [Fix service modules](./step6-services.md) - Update service-related imports
7. [Run the application](./step7-run.md) - Instructions for running with the correct PYTHONPATH

## Troubleshooting

If you encounter import errors after these fixes, check the [troubleshooting guide](./troubleshooting.md).

## Best Practices Going Forward

To maintain consistency:

1. Always use relative imports when appropriate (e.g., `from .models import User`)
2. When absolute imports are necessary, use the `virtualstack.` prefix, not `src.virtualstack.`
3. Run the application from the `src` directory using `python -m uvicorn virtualstack.main:app`
4. Alternatively, set PYTHONPATH explicitly when running from the project root 