from __future__ import annotations

import hashlib
import os
from pathlib import Path

import psycopg2

MIGRATIONS = Path(__file__).resolve().parents[1] / "eos_v2" / "infrastructure" / "db" / "migrations"


def main() -> None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    files = sorted(MIGRATIONS.glob("[0-9][0-9][0-9][0-9]_*.sql"))
    if not files:
        raise SystemExit("No v2 migrations found")

    with psycopg2.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext('eos_v2_schema_migrations'))")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS eos_v2_schema_migrations (
                    version VARCHAR(100) PRIMARY KEY,
                    checksum CHAR(64) NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            for path in files:
                version = path.stem
                sql = path.read_text(encoding="utf-8")
                checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
                cursor.execute("SELECT checksum FROM eos_v2_schema_migrations WHERE version = %s", (version,))
                row = cursor.fetchone()
                if row is not None:
                    if row[0] != checksum:
                        raise RuntimeError(f"Migration checksum mismatch: {version}")
                    continue
                cursor.execute(sql)
                cursor.execute(
                    "INSERT INTO eos_v2_schema_migrations(version, checksum) VALUES (%s, %s)",
                    (version, checksum),
                )
                print(f"applied {version}")


if __name__ == "__main__":
    main()
