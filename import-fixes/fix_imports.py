#!/usr/bin/env python3
"""
Import Fixer Script for VirtualStack

This script automatically detects and fixes import issues in a Python project,
specifically replacing 'src.virtualstack' imports with 'virtualstack' imports.

Usage:
    python fix_imports.py [--dry-run]

Options:
    --dry-run    Only show what would be changed without making changes
"""

import os
import re
import sys
import argparse
import shutil
from datetime import datetime

# Regular expressions for matching imports
IMPORT_PATTERNS = [
    re.compile(r'from src\.virtualstack\.'),
    re.compile(r'import src\.virtualstack\.'),
]

# Replacement patterns
REPLACEMENTS = [
    'from virtualstack.',
    'import virtualstack.',
]

def backup_directory(src_dir):
    """Create a timestamped backup of the src directory"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"{src_dir}_backup_{timestamp}"
    shutil.copytree(src_dir, backup_dir)
    return backup_dir

def find_python_files(directory):
    """Find all Python files in the given directory"""
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def fix_imports_in_file(file_path, dry_run=False):
    """Fix imports in a single file"""
    with open(file_path, 'r') as file:
        content = file.read()
    
    original_content = content
    
    # Apply replacements
    for pattern, replacement in zip(IMPORT_PATTERNS, REPLACEMENTS):
        content = pattern.sub(replacement, content)
    
    # Check if anything changed
    if content != original_content:
        if dry_run:
            print(f"Would fix imports in: {file_path}")
        else:
            with open(file_path, 'w') as file:
                file.write(content)
            print(f"Fixed imports in: {file_path}")
        return True
    return False

def main():
    """Main function to fix imports in the project"""
    parser = argparse.ArgumentParser(description="Fix imports in the VirtualStack project")
    parser.add_argument('--dry-run', action='store_true', help='Only show what would be changed')
    args = parser.parse_args()
    
    # Find the src directory
    src_dir = os.path.join(os.getcwd(), 'src')
    if not os.path.isdir(src_dir):
        print("Error: 'src' directory not found. Make sure you're running this from the project root.")
        sys.exit(1)
    
    # Create backup if not in dry run mode
    if not args.dry_run:
        backup_dir = backup_directory(src_dir)
        print(f"Created backup at: {backup_dir}")
    
    # Find all Python files
    python_files = find_python_files(src_dir)
    print(f"Found {len(python_files)} Python files")
    
    # Fix imports in each file
    fixed_files = 0
    for file_path in python_files:
        if fix_imports_in_file(file_path, args.dry_run):
            fixed_files += 1
    
    # Print summary
    if args.dry_run:
        print(f"\nDry run completed. {fixed_files} files would be modified.")
    else:
        print(f"\nImport fixing completed. {fixed_files} files were modified.")
        print("To run the application:")
        print("cd src && python -m uvicorn virtualstack.main:app")

if __name__ == "__main__":
    main() 