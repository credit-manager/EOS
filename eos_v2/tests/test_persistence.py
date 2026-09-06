from sqlalchemy import text

from eos_v2.infrastructure.db import Database, DatabaseConfig


def test_database_config_rejects_unsupported_scheme():
    config = DatabaseConfig("mysql://example")
    try:
        config.validate()
    except ValueError as exc:
        assert "Only PostgreSQL and SQLite" in str(exc)
    else:
        raise AssertionError("unsupported database scheme was accepted")


def test_sqlite_database_connection(tmp_path):
    database = Database(DatabaseConfig(f"sqlite:///{tmp_path / 'eos_v2.db'}"))
    assert database.check_connection() is True
    with database.engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
