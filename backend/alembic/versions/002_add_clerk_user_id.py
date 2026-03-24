"""Add clerk_user_id to users for Clerk session JWT mapping

Revision ID: 002_clerk_user
Revises: 001_initial
Create Date: 2026-03-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002_clerk_user"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("clerk_user_id", sa.String(255), nullable=True))
    op.create_index("ix_users_clerk_user_id", "users", ["clerk_user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_clerk_user_id", table_name="users")
    op.drop_column("users", "clerk_user_id")
