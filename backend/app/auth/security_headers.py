"""Security headers middleware and helper functions."""

from typing import Dict


def get_security_headers() -> Dict[str, str]:
    """
    Get common security headers for HTTP responses.

    Returns:
        Dictionary of security headers and their values
    """
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()"
    }


def get_content_security_policy() -> str:
    """
    Get Content-Security-Policy header value.

    Returns:
        CSP header value string
    """
    return (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )


def apply_security_headers(response) -> None:
    """
    Apply security headers to a FastAPI Response object.

    Args:
        response: FastAPI Response object
    """
    headers = get_security_headers()
    headers["Content-Security-Policy"] = get_content_security_policy()

    for header_name, header_value in headers.items():
        response.headers[header_name] = header_value
