"""Create IAM schema

Revision ID: 20240330_iam_schema
Revises: 
Create Date: 2024-03-30 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20240330_iam_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create IAM schema
    op.execute('CREATE SCHEMA IF NOT EXISTS iam')


def downgrade() -> None:
    # Drop IAM schema (this will cascade and drop all tables in the schema)
    op.execute('DROP SCHEMA IF EXISTS iam CASCADE') 