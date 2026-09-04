"""
EOS Locale Middleware — P64
Detects and sets locale from: query param → header → user preference → default.

Usage in main.py:
    from core.locale_middleware import LocaleMiddleware
    app.add_middleware(LocaleMiddleware)
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from core.i18n import detect_locale, set_locale


class LocaleMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that:
    1. Checks X-Locale header
    2. Checks ?lang= query parameter
    3. Falls back to Accept-Language header
    4. Defaults to English
    Sets locale for the request context.
    """

    async def dispatch(self, request: Request, call_next):
        # 1. Query parameter ?lang=ar
        lang_param = request.query_params.get("lang")

        # 2. X-Locale header
        x_locale = request.headers.get("x-locale")

        # 3. Accept-Language header
        accept_lang = request.headers.get("accept-language")

        # 4. Detect best locale
        locale = detect_locale(
            accept_language=accept_lang or "",
            user_preference=x_locale or lang_param
        )

        # Set in context
        set_locale(locale)

        # Process request
        response = await call_next(request)

        # Add locale headers to response
        response.headers["Content-Language"] = locale
        response.headers["X-Locale"] = locale
        response.headers["X-Direction"] = "rtl" if locale in ["ar", "he", "fa", "ur"] else "ltr"

        return response