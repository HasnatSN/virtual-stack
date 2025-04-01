"""create_api_keys_table.

Revision ID: 20240330_create_api_keys
Revises: 20240330_seed_permissions
Create Date: 2024-03-30 17:00:00

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic
revision = "20240330_create_api_keys"
down_revision = "20240330_seed_permissions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "api_keys",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(8), nullable=False, index=True),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        # Foreign key constraints
        sa.ForeignKeyConstraint(["user_id"], ["iam.users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam.tenants.id"], ondelete="CASCADE"),
        schema="iam",
    )

    # Add index for key_prefix for faster lookups
    op.create_index(
        op.f("ix_api_keys_key_prefix"), "api_keys", ["key_prefix"], unique=False, schema="iam"
    )

    # Add index for user_id for faster lookups of a user's API keys
    op.create_index(
        op.f("ix_api_keys_user_id"), "api_keys", ["user_id"], unique=False, schema="iam"
    )

    # Add index for tenant_id for faster lookups of tenant-scoped API keys
    op.create_index(
        op.f("ix_api_keys_tenant_id"), "api_keys", ["tenant_id"], unique=False, schema="iam"
    )


def downgrade():
    # Drop indexes
    op.drop_index(op.f("ix_api_keys_tenant_id"), table_name="api_keys", schema="iam")
    op.drop_index(op.f("ix_api_keys_user_id"), table_name="api_keys", schema="iam")
    op.drop_index(op.f("ix_api_keys_key_prefix"), table_name="api_keys", schema="iam")

    # Drop table
    op.drop_table("api_keys", schema="iam")
