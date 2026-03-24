"""Add pg_trgm extension and trigram search indexes.

Revision ID: 003_add_search_trgm_indexes
Revises: 002_add_clerk_user_id
Create Date: 2026-03-24
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "003_add_search_trgm_indexes"
down_revision = "002_add_clerk_user_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Required for similarity() and trigram GIN operator classes.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_assets_original_filename_trgm "
        "ON assets USING gin (lower(original_filename) gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_assets_city_trgm "
        "ON assets USING gin (lower(city) gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_assets_country_trgm "
        "ON assets USING gin (lower(country) gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_assets_country_trgm")
    op.execute("DROP INDEX IF EXISTS ix_assets_city_trgm")
    op.execute("DROP INDEX IF EXISTS ix_assets_original_filename_trgm")
