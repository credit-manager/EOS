"""
P74.2 Database Migration Helper
Usage:
  python db_migrate.py current       — Show current revision
  python db_migrate.py history       — Show migration history
  python db_migrate.py new "msg"     — Create new migration (autogenerate)
  python db_migrate.py upgrade       — Apply pending migrations
  python db_migrate.py downgrade -1  — Rollback last migration
  python db_migrate.py check        — Check for pending changes
"""
import sys
import subprocess

def run(cmd):
    result = subprocess.run(
        [sys.executable, "-m", "alembic"] + cmd,
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    action = sys.argv[1]

    if action == "current":
        run(["current"])
    elif action == "history":
        run(["history", "--verbose"])
    elif action == "new":
        msg = sys.argv[2] if len(sys.argv) > 2 else "auto_migration"
        run(["revision", "--autogenerate", "-m", msg])
    elif action == "upgrade":
        target = sys.argv[2] if len(sys.argv) > 2 else "head"
        run(["upgrade", target])
    elif action == "downgrade":
        target = sys.argv[2] if len(sys.argv) > 2 else "-1"
        run(["downgrade", target])
    elif action == "check":
        run(["check"])
    else:
        print(f"Unknown action: {action}")
        print(__doc__)

if __name__ == "__main__":
    main()
