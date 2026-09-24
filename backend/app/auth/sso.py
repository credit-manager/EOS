"""SSO / OAuth2/OIDC support for enterprise authentication."""
import hashlib
import logging
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx

logger = logging.getLogger("2to-eos.auth.sso")

SSO_PROVIDERS = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scopes": ["openid", "email", "profile"],
    },
    "microsoft": {
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/v1.0/me",
        "scopes": ["openid", "email", "profile"],
    },
    "okta": {
        "auth_url": "https://{domain}/oauth2/default/v1/authorize",
        "token_url": "https://{domain}/oauth2/default/v1/token",
        "userinfo_url": "https://{domain}/oauth2/default/v1/userinfo",
        "scopes": ["openid", "email", "profile"],
    },
}


class SSOService:
    """SSO service for OAuth2/OIDC authentication."""

    _state_store: dict[str, float] = {}

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    def get_auth_url(self, provider: str, redirect_uri: str) -> dict[str, str]:
        """Generate the authorization URL for SSO login."""
        if provider not in SSO_PROVIDERS:
            raise ValueError(f"Unknown SSO provider: {provider}")

        prov_config = SSO_PROVIDERS[provider]
        state = secrets.token_urlsafe(32)
        self._state_store[state] = time.time()

        params = {
            "client_id": self.config.get(f"{provider}_client_id", ""),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(prov_config["scopes"]),
            "state": state,
        }

        auth_url = prov_config["auth_url"]
        if "{domain}" in auth_url:
            auth_url = auth_url.replace("{domain}", self.config.get(f"{provider}_domain", ""))

        return {"auth_url": f"{auth_url}?{urlencode(params)}", "state": state}

    def exchange_code(self, provider: str, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange authorization code for tokens."""
        if provider not in SSO_PROVIDERS:
            raise ValueError(f"Unknown SSO provider: {provider}")

        prov_config = SSO_PROVIDERS[provider]
        token_url = prov_config["token_url"]

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(token_url, data={
                    "client_id": self.config.get(f"{provider}_client_id", ""),
                    "client_secret": self.config.get(f"{provider}_client_secret", ""),
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                })
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("SSO token exchange failed: %s", e)
            return {"error": str(e)}

    def get_user_info(self, provider: str, access_token: str) -> dict[str, Any]:
        """Get user info from SSO provider."""
        if provider not in SSO_PROVIDERS:
            raise ValueError(f"Unknown SSO provider: {provider}")

        prov_config = SSO_PROVIDERS[provider]
        userinfo_url = prov_config["userinfo_url"]

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(userinfo_url, headers={
                    "Authorization": f"Bearer {access_token}",
                })
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("SSO userinfo fetch failed: %s", e)
            return {"error": str(e)}

    def validate_state(self, state: str) -> bool:
        """Validate the OAuth state parameter."""
        if state not in self._state_store:
            return False
        created = self._state_store.pop(state)
        return (time.time() - created) < 600  # 10 min expiry
