"""Add role column to users table.

Roles: guest, user, moderator, interpreter, tenant_admin, admin
Default: 'user'

Revision ID: 0002
Create Date: 2026-04-26
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(20), nullable=False, server_default="user"))
    op.create_check_constraint(
        "user_role_check", "users",
        "role IN ('guest','user','moderator','interpreter','tenant_admin','admin')"
    )


def downgrade() -> None:
    op.drop_constraint("user_role_check", "users", type_="check")
    op.drop_column("users", "role")
