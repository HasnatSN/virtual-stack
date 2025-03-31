# Quick Fix for Import Issues

If you prefer to fix all import issues at once, you can use the following script. This is a more aggressive approach but can save time over the step-by-step process.

## Caution

- This will modify all Python files in your project
- Back up your code before running this command
- Review the changes afterward to ensure nothing was broken

## Command for macOS/Linux

```bash
# First, back up your code
cp -r src src_backup

# Then run this command from the project root to replace all import statements
find src -name "*.py" -type f -exec sed -i '' 's/from src\.virtualstack\./from virtualstack./g' {} \;
find src -name "*.py" -type f -exec sed -i '' 's/import src\.virtualstack\./import virtualstack./g' {} \;
```

## Alternative Method Using grep

If you want to see which files will be affected before making changes:

```bash
# Find all files containing the problematic import pattern
grep -r "from src\.virtualstack\." src --include="*.py"
grep -r "import src\.virtualstack\." src --include="*.py"
```

## Running the Application After Fix

After applying the fixes:

```bash
cd src
python3 -m uvicorn virtualstack.main:app
```

## Verifying Success

If the application starts without import errors, the fix was successful. You can access:

- API: http://localhost:8000/
- Documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Reverting Changes (If Needed)

If something goes wrong, you can restore from backup:

```bash
rm -rf src
mv src_backup src
``` 