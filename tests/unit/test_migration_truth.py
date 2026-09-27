"""AUDIT-007: migration inventory guard."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = REPO_ROOT / "src/youtube_extension/backend/migrations/versions"
MODELS = REPO_ROOT / "src/youtube_extension/backend/models"


def test_migration_versions_present() -> None:
    revisions = sorted(MIGRATIONS.glob("*.py"))
    assert len(revisions) >= 3, "expected at least 001-003 alembic revisions"


def test_model_package_present() -> None:
    py_models = [p for p in MODELS.glob("*.py") if p.name != "__init__.py"]
    assert len(py_models) >= 5, "backend models package should list multiple domain modules"
