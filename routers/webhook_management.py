"""P19 Webhook Management Dashboard with tenant isolation and SSRF protection."""
import ipaddress
import json
import socket
import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.auth_adapter import get_current_user
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic", tags=["Webhook Management"])


def _resolve_webhook_id(db: Session, webhook_code: str, tenant_id: str) -> str | None:
    row = db.execute(
        text("SELECT id FROM dbp_webhooks WHERE code = :code AND tenant_id = :tid"),
        {"code": webhook_code, "tid": tenant_id},
    ).fetchone()
    return row[0] if row else None


def _validate_webhook_url(target_url: str) -> None:
    """Fail closed for local/private/link-local destinations and unsafe schemes."""
    parsed = urlparse(target_url)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID_WEBHOOK_URL", "message": "Webhook URL must use HTTP or HTTPS"}})
    host = parsed.hostname.rstrip(".").lower()
    allowed = {h.strip().lower().rstrip(".") for h in __import__("os").getenv("EOS_WEBHOOK_ALLOWED_HOSTS", "").split(",") if h.strip()}
    if allowed and host not in allowed:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "WEBHOOK_HOST_NOT_ALLOWED", "message": "Webhook destination host is not allowlisted"}})
    try:
        literal = ipaddress.ip_address(host)
        addresses = [literal]
    except ValueError:
        try:
            addresses = [ipaddress.ip_address(info[4][0]) for info in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)]
        except OSError as exc:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "DNS_RESOLUTION_FAILED", "message": "Webhook destination could not be resolved"}}) from exc
    if not addresses:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "DNS_RESOLUTION_FAILED", "message": "Webhook destination could not be resolved"}})
    for addr in addresses:
        if addr.is_loopback or addr.is_private or addr.is_link_local or addr.is_multicast or addr.is_reserved or addr.is_unspecified:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "SSRF_BLOCKED", "message": "Webhook destination resolves to a non-public address"}})


def _not_found():
    return HTTPException(status_code=404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Webhook not found"}})


@router.post("/webhook-deliveries/{delivery_id}/retry", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def retry_delivery(delivery_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.execute(text(
        "SELECT d.id, d.status FROM dbp_webhook_deliveries d "
        "JOIN dbp_webhooks w ON w.id = d.webhook_id "
        "WHERE d.id = :did AND w.tenant_id = :tid"
    ), {"did": delivery_id, "tid": user["tenant_id"]}).fetchone()
    if not row:
        raise _not_found()
    if row[1] == "success":
        raise HTTPException(400, detail={"status": "error", "error": {"code": "ALREADY_SUCCESS", "message": "Delivery already succeeded"}})
    db.execute(text("UPDATE dbp_webhook_deliveries d SET status='pending', attempts=0, last_error=NULL, next_retry_at=NULL FROM dbp_webhooks w WHERE d.id=:did AND w.id=d.webhook_id AND w.tenant_id=:tid"), {"did": delivery_id, "tid": user["tenant_id"]})
    db.commit()
    return {"status": "success", "data": {"id": delivery_id, "status": "pending"}}


@router.post("/webhooks/{webhook_code}/retry-failed", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def retry_all_failed(webhook_code: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    wh_id = _resolve_webhook_id(db, webhook_code, user["tenant_id"])
    if not wh_id:
        raise _not_found()
    result = db.execute(text("UPDATE dbp_webhook_deliveries SET status='pending', attempts=0, last_error=NULL, next_retry_at=NULL WHERE webhook_id=:wid AND status='failed'"), {"wid": wh_id})
    db.commit()
    return {"status": "success", "data": {"retrying_count": result.rowcount}}


@router.post("/webhooks/{webhook_code}/test", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def test_webhook(webhook_code: str, body: dict | None = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    body = body or {}
    wh = db.execute(text(
        "SELECT id, target_url, entity_code, secret, custom_headers FROM dbp_webhooks WHERE code=:code AND tenant_id=:tid"
    ), {"code": webhook_code, "tid": user["tenant_id"]}).fetchone()
    if not wh:
        raise _not_found()
    target_url, entity_code, secret, headers = wh[1], wh[2], wh[3], wh[4] or {}
    _validate_webhook_url(target_url)
    test_event_type = body.get("event_type", "record.created")
    event_id = str(uuid.uuid4())
    db.execute(text(
        "INSERT INTO dbp_events (id, tenant_id, event_type, entity_code, record_id, user_id, payload, created_at) "
        "VALUES (:id, :tid, :et, :ec, 'test-record', :uid, :payload, NOW())"
    ), {"id": event_id, "tid": user["tenant_id"], "et": test_event_type, "ec": entity_code, "uid": user.get("id"), "payload": json.dumps(body.get("payload", {"test": True, "message": "Webhook test event"}))})
    delivery_id = str(uuid.uuid4())
    db.execute(text("INSERT INTO dbp_webhook_deliveries (id, webhook_id, event_id, status, attempts) VALUES (:id,:wid,:eid,'pending',0)"), {"id": delivery_id, "wid": wh[0], "eid": event_id})
    db.flush()
    import hashlib
    import hmac
    import httpx
    payload_str = json.dumps(body.get("payload", {"test": True, "message": "Webhook test event"}))
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    if secret:
        req_headers["X-DBP-Signature"] = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
    try:
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            resp = client.post(target_url, content=payload_str, headers=req_headers)
        success = resp.status_code < 400
        db.execute(text("UPDATE dbp_webhook_deliveries SET status=:st, attempts=1, last_response_code=:code WHERE id=:did AND webhook_id=:wid"), {"did": delivery_id, "wid": wh[0], "st": "success" if success else "failed", "code": resp.status_code})
    except Exception as exc:
        db.execute(text("UPDATE dbp_webhook_deliveries SET status='failed', attempts=1, last_response_code=NULL, last_error=:err WHERE id=:did AND webhook_id=:wid"), {"did": delivery_id, "wid": wh[0], "err": str(exc)[:500]})
        success = False
    db.commit()
    return {"status": "success", "data": {"delivery_id": delivery_id, "event_id": event_id, "test_result": "success" if success else "failed"}}


@router.get("/webhooks/{webhook_code}/health", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def webhook_health(webhook_code: str, hours: int | None = 24, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if hours is None or hours < 1 or hours > 24 * 365:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID_PERIOD", "message": "hours must be between 1 and 8760"}})
    wh_id = _resolve_webhook_id(db, webhook_code, user["tenant_id"])
    if not wh_id:
        raise _not_found()
    health = db.execute(text("SELECT COUNT(*), COUNT(*) FILTER (WHERE status='success'), COUNT(*) FILTER (WHERE status='failed'), COUNT(*) FILTER (WHERE status='pending'), COUNT(*) FILTER (WHERE status='retrying'), AVG(attempts) FILTER (WHERE status='success'), MAX(attempts), COUNT(DISTINCT event_id) FROM dbp_webhook_deliveries WHERE webhook_id=:wid AND created_at >= NOW() - (:hrs || ' hours')::interval"), {"wid": wh_id, "hrs": str(hours)}).fetchone()
    error_breakdown = db.execute(text("SELECT last_response_code, COUNT(*) FROM dbp_webhook_deliveries WHERE webhook_id=:wid AND status='failed' AND created_at >= NOW() - (:hrs || ' hours')::interval GROUP BY last_response_code ORDER BY COUNT(*) DESC"), {"wid": wh_id, "hrs": str(hours)}).fetchall()
    total, success = health[0] or 0, health[1] or 0
    return {"status": "success", "data": {"webhook_code": webhook_code, "period_hours": hours, "total_deliveries": total, "success_count": success, "failed_count": health[2] or 0, "pending_count": health[3] or 0, "retrying_count": health[4] or 0, "success_rate": round(success / total * 100, 2) if total else 0, "avg_attempts_to_success": round(float(health[5]), 2) if health[5] else None, "max_attempts": health[6] or 0, "unique_events": health[7] or 0, "error_breakdown": [{"response_code": e[0], "count": e[1]} for e in error_breakdown]}}
