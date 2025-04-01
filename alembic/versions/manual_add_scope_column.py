"""Manually add scope column to api keys table.

Revision ID: manual_add_scope_column
Revises: 20240330_create_api_keys
Create Date: 2025-04-01 15:15:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

# Import Enum type for PostgreSQL
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "manual_add_scope_column"
down_revision: Union[str, None] = "20240330_create_api_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define the Enum type name matching the model (important for SQLAlchemy/PostgreSQL)
api_key_scope_enum = postgresql.ENUM("GLOBAL", "TENANT", name="api_key_scope", create_type=False)


def upgrade() -> None:
    # Create the ENUM type first
    api_key_scope_enum.create(op.get_bind(), checkfirst=True)

    # Add the scope column to the api_keys table in the iam schema
    op.add_column(
        "api_keys",
        sa.Column(
            "scope",
            api_key_scope_enum,
            nullable=False,
            # Set a server default matching the model's default
            server_default="TENANT",
        ),
        schema="iam",
    )


def downgrade() -> None:
    # Drop the scope column from the api_keys table in the iam schema
    op.drop_column("api_keys", "scope", schema="iam")

    # Drop the ENUM type
    api_key_scope_enum.drop(op.get_bind(), checkfirst=True)
    # Optionally drop the ENUM type if no longer needed (be careful if other tables might use it)
    # op.execute("DROP TYPE IF EXISTS api_key_scope")
