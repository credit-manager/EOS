from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse


def main() -> None:
    environment = os.getenv("EOS_ENV", "development").lower()
    auth_mode = os.getenv("EOS_AUTH_MODE", "hs256").lower()
    if environment == "production":
        required = ("DATABASE_URL", "EOS_ALLOWED_HOSTS", "EOS_CORS_ORIGINS", "EOS_METRICS_TOKEN")
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise SystemExit(f"production security gate failed: missing {', '.join(missing)}")
        if len(os.environ["EOS_METRICS_TOKEN"]) < 16:
            raise SystemExit("production security gate failed: weak metrics token")
        if auth_mode != "oidc":
            raise SystemExit("production security gate failed: EOS_AUTH_MODE must be oidc")
        oidc_required = ("EOS_OIDC_ISSUER", "EOS_OIDC_AUDIENCE", "EOS_OIDC_JWKS_URL")
        oidc_missing = [name for name in oidc_required if not os.getenv(name)]
        if oidc_missing:
            raise SystemExit(f"production security gate failed: missing {', '.join(oidc_missing)}")
        for name in ("EOS_OIDC_ISSUER", "EOS_OIDC_JWKS_URL"):
            if urlparse(os.environ[name]).scheme.lower() != "https":
                raise SystemExit(f"production security gate failed: {name} must use HTTPS")
    source = Path("eos_v2/application/identity/authentication.py").read_text(encoding="utf-8")
    if 'algorithms=["none"]' in source:
        raise SystemExit("production security gate failed: unsecured JWT algorithm")
    if "jwt.decode(" not in source:
        raise SystemExit("production security gate failed: token validation missing")
    if 'algorithms=["HS256"]' not in source or 'algorithms=["RS256"]' not in source:
        raise SystemExit("production security gate failed: explicit HS256 and RS256 validation paths required")
    print("production security gate: PASS")


if __name__ == "__main__":
    main()
