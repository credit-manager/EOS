"""EOS Database Backup Script — works with PostgreSQL and SQLite."""
import gzip
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def backup_database():
    backup_dir = Path(os.getenv("BACKUP_DIR", "./backups"))
    backup_dir.mkdir(exist_ok=True)

    db_url = os.getenv("DATABASE_URL", "sqlite:///./eos_demo.db")
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    output = None
    if db_url.startswith("postgresql"):
        # Parse postgres URL: postgresql://user:pass@host:port/dbname
        from urllib.parse import urlparse
        parsed = urlparse(db_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        user = parsed.username or "eos_user"
        dbname = parsed.path.lstrip("/") or "eos_db"
        password = parsed.password or ""

        output = backup_dir / f"eos_{date_str}.sql.gz"
        env = os.environ.copy()
        env["PGPASSWORD"] = password
        with gzip.open(output, "wt") as f:
            subprocess.run(
                ["pg_dump", "-h", host, "-p", str(port), "-U", user, "-d", dbname],
                stdout=f,
                env=env,
                check=True,
            )
    elif db_url.startswith("sqlite"):
        db_path = db_url.replace("sqlite:///", "").replace("sqlite:////", "/")
        output = backup_dir / f"eos_{date_str}.db.gz"
        with gzip.open(output, "wb") as f:
            with open(db_path, "rb") as src:
                shutil.copyfileobj(src, f)
    else:
        print(f"Unsupported database URL scheme: {db_url}")
        return

    # Cleanup old backups
    retention = int(os.getenv("RETENTION_DAYS", "30"))
    cutoff = datetime.now().timestamp() - (retention * 86400)
    removed = 0
    for f in backup_dir.glob("eos_*"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1

    print(f"Backup completed: {output}")
    print(f"Removed {removed} old backups (retention: {retention} days)")


if __name__ == "__main__":
    backup_database()
