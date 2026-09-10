from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_db_role_is_distinct_from_migration_role():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    init_db = (ROOT / "scripts/init-db.sh").read_text(encoding="utf-8")

    assert "EOS_DB_RUNTIME_USER" in compose
    assert "EOS_DB_RUNTIME_PASSWORD" in compose
    assert "EOS_DB_RUNTIME_USER must be different from POSTGRES_USER" in init_db
    assert "ALTER DEFAULT PRIVILEGES FOR ROLE" in init_db


def test_migrations_run_as_separate_service():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    entrypoint = (ROOT / "docker/entrypoint.sh").read_text(encoding="utf-8")

    assert "migrate:" in compose
    assert 'entrypoint: ["/app/docker/migrate-entrypoint.sh"]' in compose
    assert "service_completed_successfully" in compose
    assert "alembic upgrade head" not in entrypoint


def test_production_migration_entrypoint_is_present_and_fails_closed():
    migration_entrypoint = (ROOT / "docker/migrate-entrypoint.sh").read_text(encoding="utf-8")

    assert "set -eu" in migration_entrypoint
    assert 'DATABASE_URL:-' in migration_entrypoint
    assert "alembic upgrade head" in migration_entrypoint


def test_production_image_runs_as_non_root_and_packages_migration_entrypoint():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "/app/docker/migrate-entrypoint.sh" in dockerfile
    assert "USER eos" in dockerfile
    assert "chmod 0755 /app/docker/entrypoint.sh /app/docker/migrate-entrypoint.sh" in dockerfile
