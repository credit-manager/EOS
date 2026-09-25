"""Security Audit — periodic security checks for the EOS instance."""
import logging
from datetime import datetime, UTC

logger = logging.getLogger("2to-eos.security")

def run_security_audit(db_session) -> dict:
    """Run a comprehensive security audit."""
    results = {
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": [],
        "score": 0,
        "max_score": 0,
    }

    # Check 1: JWT Secret strength
    from .config import get_settings
    settings = get_settings()
    secret_score = 0
    if len(settings.jwt_secret) >= 32:
        secret_score += 1
    if settings.jwt_secret != "development-only-secret":
        secret_score += 1
    if settings.app_env == "production" and secret_score < 2:
        logger.warning("JWT secret is weak for production")
    results["checks"].append({
        "name": "JWT Secret Strength",
        "status": "pass" if secret_score >= 2 else "fail",
        "score": secret_score,
        "max_score": 2,
    })
    results["score"] += secret_score
    results["max_score"] += 2

    # Check 2: HTTPS enforcement
    https_score = 1 if settings.app_env == "production" else 0
    results["checks"].append({
        "name": "HTTPS Enforcement",
        "status": "pass" if https_score else "warn",
        "score": https_score,
        "max_score": 1,
    })
    results["score"] += https_score
    results["max_score"] += 1

    # Check 3: CORS configuration
    cors_score = 1 if "*" not in settings.cors_origin_list else 0
    results["checks"].append({
        "name": "CORS Configuration",
        "status": "pass" if cors_score else "fail",
        "score": cors_score,
        "max_score": 1,
    })
    results["score"] += cors_score
    results["max_score"] += 1

    # Check 4: Database security
    db_score = 1 if not settings.database_url.startswith("sqlite") or settings.app_env != "production" else 0
    results["checks"].append({
        "name": "Database Security",
        "status": "pass" if db_score else "warn",
        "score": db_score,
        "max_score": 1,
        "detail": "SQLite is not recommended for production" if not db_score else "PostgreSQL detected",
    })
    results["score"] += db_score
    results["max_score"] += 1

    # Check 5: Rate limiting
    rate_score = 1 if settings.rate_limit_auth_per_minute > 0 else 0
    results["checks"].append({
        "name": "Rate Limiting",
        "status": "pass" if rate_score else "fail",
        "score": rate_score,
        "max_score": 1,
    })
    results["score"] += rate_score
    results["max_score"] += 1

    # Check 6: SSO configuration
    sso_score = 0
    if settings.google_client_id:
        sso_score += 1
    if settings.microsoft_client_id:
        sso_score += 1
    results["checks"].append({
        "name": "SSO Configuration",
        "status": "pass" if sso_score > 0 else "warn",
        "score": min(sso_score, 1),
        "max_score": 1,
    })
    results["score"] += min(sso_score, 1)
    results["max_score"] += 1

    return results
