#!/usr/bin/env python
import asyncio
import sys
import os
import logging

# Add project root to sys.path to allow absolute imports from 'src'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

# Must set RUN_ENV before importing settings
os.environ["RUN_ENV"] = "development"
from src.virtualstack.db.session import SessionLocal # Import the same SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Checking database readiness...")
    async with SessionLocal() as session:
        try:
            # Try selecting from the users table
            await session.execute(text("SELECT 1 FROM iam.users LIMIT 1"))
            logger.info("Successfully connected and found 'iam.users' table.")
            sys.exit(0) # Success
        except ProgrammingError as e:
            # Catch the specific error if the table doesn't exist
            if "relation \"iam.users\" does not exist" in str(e):
                logger.error("Verification FAILED: 'iam.users' table does not exist according to SessionLocal.")
            else:
                logger.error(f"Database connection/query failed with unexpected error: {e}", exc_info=True)
            sys.exit(1) # Failure
        except Exception as e:
            logger.error(f"An unexpected error occurred during DB check: {e}", exc_info=True)
            sys.exit(1) # Failure

if __name__ == "__main__":
    asyncio.run(main()) 