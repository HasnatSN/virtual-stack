"""Create IAM tables.

Revision ID: 20240330_iam_tables
Revises: 20240330_iam_schema
Create Date: 2024-03-30 16:05:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20240330_iam_tables"
down_revision: Union[str, None] = "20240330_iam_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.UniqueConstraint("slug", name="uq_tenant_slug"),
        sa.Index("ix_tenant_name", "name"),
        sa.Index("ix_tenant_slug", "slug"),
        schema="iam",
    )

    # Create permissions table
    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("module", sa.String(100), nullable=False),
        sa.UniqueConstraint("code", name="uq_permission_code"),
        sa.Index("ix_permission_code", "code"),
        sa.Index("ix_permission_module", "module"),
        schema="iam",
    )

    # Create tenant roles table
    op.create_table(
        "tenant_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system_role", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("iam.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("tenant_id", "name", name="uq_tenant_role_name"),
        sa.Index("ix_tenant_role_name", "name"),
        schema="iam",
    )

    # Create tenant role permissions table
    op.create_table(
        "tenant_role_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column(
            "tenant_role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("iam.tenant_roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "permission_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("iam.permissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("tenant_role_id", "permission_id", name="uq_tenant_role_permission"),
        schema="iam",
    )

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, default=False),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("email", name="uq_user_email"),
        sa.Index("ix_user_email", "email"),
        schema="iam",
    )

    # Create user_tenant_roles table
    op.create_table(
        "user_tenant_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("iam.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("iam.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("iam.tenant_roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "tenant_id", "tenant_role_id", name="uq_user_tenant_role"),
        schema="iam",
    )


def downgrade() -> None:
    # Drop tables in reverse order of creation
    op.drop_table("user_tenant_roles", schema="iam")
    op.drop_table("users", schema="iam")
    op.drop_table("tenant_role_permissions", schema="iam")
    op.drop_table("tenant_roles", schema="iam")
    op.drop_table("permissions", schema="iam")
    op.drop_table("tenants", schema="iam")
