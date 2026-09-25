"""Production startup script — initializes the application."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 60)
    print("  2TO EOS — Production Startup")
    print("=" * 60)

    from app.config import get_settings
    settings = get_settings()

    # Step 1: Validate settings
    print("\n[1/5] Validating configuration...")
    errors = []
    if settings.app_env == "production":
        if settings.jwt_secret == "development-only-secret":
            errors.append("JWT_SECRET must be changed for production")
        if len(settings.jwt_secret) < 32:
            errors.append("JWT_SECRET must be at least 32 characters")
        if not settings.stripe_secret_key or settings.stripe_secret_key.startswith("sk_test"):
            print("  WARNING: Stripe test keys detected")
        if not settings.sendgrid_api_key:
            print("  WARNING: SendGrid API key not configured — emails won't be sent")
        if not settings.openai_api_key:
            print("  WARNING: OpenAI API key not configured — AI features disabled")

    if errors:
        print("  FATAL ERRORS:")
        for e in errors:
            print(f"    - {e}")
        sys.exit(1)
    print("  Configuration OK")

    # Step 2: Create tables
    print("\n[2/5] Creating database tables...")
    from app.db import Base, engine
    Base.metadata.create_all(bind=engine)
    print("  Tables created")

    # Step 3: Run migrations
    print("\n[3/5] Running migrations...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if result.returncode == 0:
        print("  Migrations applied")
    else:
        print(f"  Migration warning: {result.stderr[:200]}")

    # Step 4: Seed data
    print("\n[4/5] Seeding database...")
    from scripts.seed import run_seed
    try:
        run_seed()
    except Exception as e:
        print(f"  Seed skipped: {e}")

    # Step 5: Start server
    print("\n[5/5] Starting server...")
    print(f"  Environment: {settings.app_env}")
    print(f"  Database: {settings.database_url.split('@')[-1] if '@' in settings.database_url else 'local'}")
    print(f"  CORS: {settings.cors_origins}")
    print()

    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        workers=4 if settings.app_env == "production" else 1,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
