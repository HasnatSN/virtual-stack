#!/usr/bin/env python
import asyncio
import sys
import os
import logging

# Add project root to sys.path to allow absolute imports from 'src'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from sqlalchemy.ext.asyncio import AsyncSession

# Must set RUN_ENV before importing settings
os.environ["RUN_ENV"] = "development" 
from src.virtualstack.db.session import SessionLocal
from src.virtualstack.db.init_db import seed_initial_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting standalone data seeding...")
    async with SessionLocal() as db_session:
        try:
            await seed_initial_data(db_session)
            await db_session.commit()
            logger.info("Standalone data seeding committed successfully.")
        except Exception as e:
            logger.error(f"Standalone data seeding failed: {e}. Rolling back...", exc_info=True)
            await db_session.rollback()
            sys.exit(1) # Exit with error code

if __name__ == "__main__":
    asyncio.run(main()) 