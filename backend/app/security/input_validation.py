"""Input Validation — sanitize and validate all user inputs."""
import re
from typing import Any


class InputValidator:
    """Validate and sanitize user inputs."""

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize a string input."""
        if not isinstance(value, str):
            return ""
        # Remove control characters
        value = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", value)
        return value[:max_length].strip()

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_sql_injection(value: str) -> bool:
        """Check for SQL injection patterns."""
        dangerous_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|FETCH|DECLARE|TRUNCATE)\b)",
            r"(--|;|/\*|\*/|@@|@)",
            r"(\b(OR|AND)\b\s+\d+\s*=\s*\d+)",
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return False
        return True

    @staticmethod
    def validate_xss(value: str) -> bool:
        """Check for XSS patterns."""
        xss_patterns = [
            r"<script[^>]*>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
        ]
        for pattern in xss_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return False
        return True

    @staticmethod
    def sanitize_dict(data: dict[str, Any], max_depth: int = 5) -> dict[str, Any]:
        """Recursively sanitize a dictionary."""
        if max_depth <= 0:
            return {}
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = InputValidator.sanitize_string(value)
            elif isinstance(value, dict):
                result[key] = InputValidator.sanitize_dict(value, max_depth - 1)
            elif isinstance(value, list):
                result[key] = [
                    InputValidator.sanitize_string(v) if isinstance(v, str) else v
                    for v in value[:100]  # Limit list size
                ]
            else:
                result[key] = value
        return result
