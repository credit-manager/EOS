from __future__ import annotations

import os
from pathlib import Path


def main() -> None:
    environment = os.getenv("EOS_ENV", "development").lower()
    if environment == "production":
        required = ("DATABASE_URL", "EOS_SECRET_KEY", "EOS_ALLOWED_HOSTS", "EOS_CORS_ORIGINS")
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise SystemExit(f"production security gate failed: missing {', '.join(missing)}")
        if len(os.environ["EOS_SECRET_KEY"]) < 32:
            raise SystemExit("production security gate failed: weak secret")
    source = Path("eos_v2/application/identity/authentication.py").read_text(encoding="utf-8")
    if "algorithms=[\"none\"]" in source:
        raise SystemExit("production security gate failed: unsecured JWT algorithm")
    if "jwt.decode(" not in source:
        raise SystemExit("production security gate failed: token validation missing")
    print("production security gate: PASS")


if __name__ == "__main__":
    main()
