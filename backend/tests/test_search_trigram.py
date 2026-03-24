from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
SEARCH_API = BACKEND_ROOT / "app" / "api" / "v1" / "search.py"
MIGRATION = BACKEND_ROOT / "alembic" / "versions" / "003_add_search_trgm_indexes.py"


def test_search_api_uses_postgres_similarity_ranking():
    text = SEARCH_API.read_text(encoding="utf-8")
    assert "func.similarity" in text
    assert "func.greatest" in text
    assert "_is_postgres" in text


def test_migration_enables_pg_trgm_and_creates_indexes():
    text = MIGRATION.read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS pg_trgm" in text
    assert "ix_assets_original_filename_trgm" in text
    assert "ix_assets_city_trgm" in text
    assert "ix_assets_country_trgm" in text


def test_migration_has_reversible_downgrade():
    text = MIGRATION.read_text(encoding="utf-8")
    assert "DROP INDEX IF EXISTS ix_assets_country_trgm" in text
    assert "DROP INDEX IF EXISTS ix_assets_city_trgm" in text
    assert "DROP INDEX IF EXISTS ix_assets_original_filename_trgm" in text
