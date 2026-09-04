import pytest
from fastapi import HTTPException

from routers.webhook_management import _validate_webhook_url


def test_webhook_blocks_loopback_ip():
    with pytest.raises(HTTPException) as exc:
        _validate_webhook_url("http://127.0.0.1:8000/hook")
    assert exc.value.status_code == 400
    assert exc.value.detail["error"]["code"] == "SSRF_BLOCKED"


def test_webhook_blocks_private_ip():
    with pytest.raises(HTTPException) as exc:
        _validate_webhook_url("http://10.0.0.10/hook")
    assert exc.value.detail["error"]["code"] == "SSRF_BLOCKED"
