"""
2TO EOS Developer SDK - Python client library.

Usage:
    from eos_sdk import EOSClient, EOSConfig

    config = EOSConfig(api_key="eos_...", base_url="http://localhost:8000")
    client = EOSClient(config)

    # Business objects
    projects = client.projects.list()
    project = client.projects.get(project_id)

    # Financial
    trial_balance = client.financial.trial_balance()
    pnl = client.financial.profit_and_loss()

    # AI
    answer = client.ai.ask("ما 순현재가치를 للمشروع؟")

    # Webhooks
    client.webhooks.create({"url": "https://...", "events": ["*"]})
    client.webhooks.list()

    # Events
    events = client.events.list(event_type="construction.project.updated")
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class EOSConfig:
    """SDK configuration."""

    api_key: str
    base_url: str = "http://localhost:8000"
    timeout_seconds: float = 30.0
    default_tenant_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.base_url.endswith("/"):
            self.base_url = self.base_url.rstrip("/")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class EOSError(Exception):
    """Base SDK error."""

    def __init__(self, message: str, *, status_code: int | None = None, detail: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class EOSAuthError(EOSError):
    """401 / 403."""

    pass


class EOSNotFoundError(EOSError):
    """404."""

    pass


class EOSRateLimitError(EOSError):
    """429."""

    pass


class EOSValidationError(EOSError):
    """422 / validation."""

    pass


# ---------------------------------------------------------------------------
# HTTP client wrapper
# ---------------------------------------------------------------------------

class _HTTPClient:
    """Thin httpx wrapper with auth header, error mapping, retries."""

    def __init__(self, config: EOSConfig) -> None:
        if httpx is None:
            raise ImportError("Install eos-sdk[http] to use the SDK: pip install httpx")
        self._config = config
        self._client = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            Headers={"Authorization": f"Bearer {config.api_key}"},
        )

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any] | list[Any]:
        url = f"/api/v1{path}"
        try:
            resp = self._client.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            raise EOSError("Request timed out", detail=str(exc)) from exc
        except httpx.NetworkError as exc:
            raise EOSError("Network error", detail=str(exc)) from exc

        self._raise_for_status(resp)
        return self._decode(resp)

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        return self.request("GET", path, params=params)

    def post(self, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        return self.request("POST", path, json=json_body)

    def patch(self, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        return self.request("PATCH", path, json=json_body)

    def delete(self, path: str) -> None:
        resp = self._client.request("DELETE", f"/api/v1{path}")
        self._raise_for_status(resp)

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code == 401 or resp.status_code == 403:
            raise EOSAuthError(resp.json().get("detail", "Unauthorized"), status_code=resp.status_code)
        if resp.status_code == 404:
            raise EOSNotFoundError(resp.json().get("detail", "Not found"), status_code=404)
        if resp.status_code == 429:
            raise EOSRateLimitError(resp.json().get("detail", "Rate limited"), status_code=429)
        if resp.status_code >= 400:
            detail = resp.json().get("detail") if resp.headers.get("content-type", "").startswith("application/json") else resp.text
            raise EOSError(detail or "Request failed", status_code=resp.status_code, detail=detail)

    @staticmethod
    def _decode(resp: httpx.Response) -> dict[str, Any] | list[Any]:
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return {}


# ---------------------------------------------------------------------------
# Sub-clients
# ---------------------------------------------------------------------------

class ProjectsClient:
    def __init__(self, http: _HTTPClient) -> None:
        self._http = http

    def list(self, limit: int = 50, offset: int = 0, status: str | None = None) -> list[dict]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        return self._http.get("/construction/projects", params=params)

    def get(self, project_id: UUID | str) -> dict:
        return self._http.get(f"/construction/projects/{project_id}")

    def create(self, code: str, name: str, **kwargs: Any) -> dict:
        payload: dict[str, Any] = {"code": code, "name": name}
        payload.update(kwargs)
        return self._http.post("/construction/projects", json_body=payload)

    def update(self, project_id: UUID | str, **kwargs: Any) -> dict:
        return self._http.patch(f"/construction/projects/{project_id}", json_body=kwargs)

    def delete(self, project_id: UUID | str) -> None:
        self._http.delete(f"/construction/projects/{project_id}")


class ContractsClient:
    def __init__(self, http: _HTTPClient) -> None:
        self._http = http

    def list(self, project_id: UUID | str | None = None, limit: int = 50) -> list[dict]:
        params: dict[str, Any] = {"limit": limit}
        if project_id:
            params["project_id"] = str(project_id)
        return self._http.get("/construction/contracts", params=params)

    def get(self, contract_id: UUID | str) -> dict:
        return self._http.get(f"/construction/contracts/{contract_id}")

    def create(self, project_id: UUID | str, contract_number: str, title: str,
               counterparty: str, **kwargs: Any) -> dict:
        payload = {"project_id": str(project_id), "contract_number": contract_number,
                   "title": title, "counterparty": counterparty, **kwargs}
        return self._http.post("/construction/contracts", json_body=payload)


class ProcurementClient:
    def __init__(self, http: _HTTPClient) -> None:
        self._http = http

    def list(self, project_id: UUID | str | None = None, limit: int = 50) -> list[dict]:
        params: dict[str, Any] = {"limit": limit}
        if project_id:
            params["project_id"] = str(project_id)
        return self._http.get("/construction/procurements", params=params)

    def get(self, procurement_id: UUID | str) -> dict:
        return self._http.get(f"/construction/procurements/{procurement_id}")

    def create(self, project_id: UUID | str, requisition_number: str, title: str,
               **kwargs: Any) -> dict:
        payload = {"project_id": str(project_id), "requisition_number": requisition_number,
                   "title": title, **kwargs}
        return self._http.post("/construction/procurements", json_body=payload)


class PackClient:
    """Construction Pack analytics & AI endpoints."""

    def __init__(self, http: _HTTPClient) -> None:
        self._http = http

    def info(self) -> dict:
        return self._http.get("/construction/pack/info")

    def project_health(self, project_id: UUID | str) -> dict:
        return self._http.get(f"/construction/pack/projects/{project_id}/health")

    def project_margin(self, project_id: UUID | str) -> dict:
        return self._http.get(f"/construction/pack/projects/{project_id}/margin")

    def cash_projection(self, months: int = 3) -> dict:
        return self._http.get("/construction/pack/dashboards/cash-projection", params={"months": months})

    def procurement_pipeline(self, project_id: UUID | str | None = None) -> dict:
        params = {}
        if project_id:
            params["project_id"] = str(project_id)
        return self._http.get("/construction/pack/procurement/pipeline", params=params)

    def contracts_status(self, project_id: UUID | str | None = None) -> dict:
        params = {}
        if project_id:
            params["project_id"] = str(project_id)
        return self._http.get("/construction/pack/contracts/status", params=params)

    def claims_kpi(self, project_id: UUID | str | None = None) -> dict:
        params = {}
        if project_id:
            params["project_id"] = str(project_id)
        return self._http.get("/construction/pack/claims/kpi", params=params)

    def rules(self) -> list[dict]:
        return self._http.get("/construction/pack/rules")

    def analyze_project(self, project_id: UUID | str) -> dict:
        return self._http.post(f"/construction/pack/analyze/{project_id}")


class FinancialClient:
    """Thin wrapper around financial core endpoints (if exposed)."""

    def __init__(self, http: _HTTPClient) -> None:
        self._http = http

    def trial_balance(self) -> dict:
        # Example endpoint; adjust path to real implementation
        return self._http.get("/financial/trial-balance")

    def profit_and_loss(self) -> dict:
        return self._http.get("/financial/profit-loss")


class AIClient:
    """Ask EOS natural-language layer."""

    def __init__(self, http: _HTTPClient) -> None:
        self._http = http

    def ask(self, query: str, context: dict[str, Any] | None = None) -> dict:
        payload = {"query": query}
        if context:
            payload["context"] = context
        return self._http.post("/ai/ask", json_body=payload)


class WebhooksClient:
    def __init__(self, http: _HTTPClient) -> None:
        self._http = http

    def list(self, app_id: str | None = None) -> list[dict]:
        params: dict[str, Any] = {}
        if app_id:
            params["app_id"] = app_id
        return self._http.get("/sdk/webhooks", params=params)

    def create(self, url: str, events: list[str], name: str = "webhook") -> dict:
        return self._http.post("/sdk/webhooks", json_body={"url": url, "events": events, "name": name})


class EventsClient:
    def __init__(self, http: _HTTPClient) -> None:
        self._http = http

    def list(self, event_type: str | None = None, status: str | None = None,
             limit: int = 50) -> list[dict]:
        params: dict[str, Any] = {"limit": limit}
        if event_type:
            params["event_type"] = event_type
        if status:
            params["status"] = status
        return self._http.get("/sdk/events", params=params)

    def stats(self) -> dict:
        return self._http.get("/sdk/events/stats")


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------

class EOSClient:
    """Main entry point for the 2TO EOS Developer SDK."""

    def __init__(self, config: EOSConfig | None = None, **config_kwargs: Any) -> None:
        if config is None:
            config = EOSConfig(**config_kwargs)
        self._config = config
        self._http = _HTTPClient(config)
        self.projects = ProjectsClient(self._http)
        self.contracts = ContractsClient(self._http)
        self.procurement = ProcurementClient(self._http)
        self.pack = PackClient(self._http)
        self.financial = FinancialClient(self._http)
        self.ai = AIClient(self._http)
        self.webhooks = WebhooksClient(self._http)
        self.events = EventsClient(self._http)

    @property
    def config(self) -> EOSConfig:
        return self._config

    def close(self) -> None:
        self._http._client.close()

    def __enter__(self) -> "EOSClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Convenience helper
# ---------------------------------------------------------------------------

def create_client(api_key: str, base_url: str = "http://localhost:8000", **kwargs: Any) -> EOSClient:
    """Create an EOSClient with minimal arguments."""
    return EOSClient(EOSConfig(api_key=api_key, base_url=base_url, **kwargs))
