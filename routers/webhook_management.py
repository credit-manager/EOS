"""
P19 Webhook Management Dashboard

Additional endpoints beyond P12 basic CRUD:
- Delivery history with status, response codes, errors (enhanced with filters)
- Webhook health metrics (success/failure rates, retry stats)
- Retry failed deliveries
- Test webhook (send sample event)

All webhook_id params use webhook_code to match P12 conventions.
"""
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(
    prefix="/api/v1/dynamic",
    tags=["Webhook Management"],
)


def _resolve_webhook_id(db: Session, webhook_code: str) -> str | None:
    """Resolve webhook code to internal ID."""
    row = db.execute(
        text("SELECT id FROM dbp_webhooks WHERE code = :code"),
        {"code": webhook_code},
    ).fetchone()
    return row[0] if row else None


# ──────────────────────────────────────────────────────────────
# RETRY FAILED DELIVERIES
# ──────────────────────────────────────────────────────────────

@router.post(
    "/webhook-deliveries/{delivery_id}/retry",
    dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)],
)
async def retry_delivery(
    delivery_id: str,
    user: dict | None=None,
    db: Session = Depends(get_db),
):
    """Manually retry a failed delivery."""
    row = db.execute(
        text("SELECT id, webhook_id, event_id, status FROM dbp_webhook_deliveries WHERE id = :did"),
        {"did": delivery_id},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": "Delivery not found"},
        })

    if row[3] == "success":
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "ALREADY_SUCCESS", "message": "Delivery already succeeded"},
        })

    db.execute(
        text(
            "UPDATE dbp_webhook_deliveries "
            "SET status='pending', attempts=0, last_error=NULL, next_retry_at=NULL "
            "WHERE id = :did"
        ),
        {"did": delivery_id},
    )
    db.commit()

    return {"status": "success", "data": {"id": delivery_id, "status": "pending"}}


# ──────────────────────────────────────────────────────────────
# RETRY ALL FAILED for a webhook
# ──────────────────────────────────────────────────────────────

@router.post(
    "/webhooks/{webhook_code}/retry-failed",
    dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)],
)
async def retry_all_failed(
    webhook_code: str,
    user: dict | None=None,
    db: Session = Depends(get_db),
):
    """Retry all failed deliveries for a webhook."""
    wh_id = _resolve_webhook_id(db, webhook_code)
    if not wh_id:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": "Webhook not found"},
        })

    result = db.execute(
        text(
            "UPDATE dbp_webhook_deliveries "
            "SET status='pending', attempts=0, last_error=NULL, next_retry_at=NULL "
            "WHERE webhook_id = :wid AND status = 'failed'"
        ),
        {"wid": wh_id},
    )
    db.commit()

    return {
        "status": "success",
        "data": {"retrying_count": result.rowcount},
    }


# ──────────────────────────────────────────────────────────────
# TEST WEBHOOK
# ──────────────────────────────────────────────────────────────

@router.post(
    "/webhooks/{webhook_code}/test",
    dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)],
)
async def test_webhook(
    webhook_code: str,
    body: dict | None = None,
    user: dict | None=None,
    db: Session = Depends(get_db),
):
    """Send a test event to the webhook."""
    if body is None:
        body = {}
    wh = db.execute(
        text("SELECT id, target_url, entity_code, secret, custom_headers "
             "FROM dbp_webhooks WHERE code = :code"),
        {"code": webhook_code},
    ).fetchone()

    if not wh:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": "Webhook not found"},
        })

    target_url, entity_code = wh[1], wh[2]
    secret, headers = wh[3], wh[4] or {}

    test_event_type = body.get("event_type", "record.created")

    event_id = str(uuid.uuid4())
    db.execute(
        text(
            "INSERT INTO dbp_events (id, tenant_id, event_type, entity_code, "
            "record_id, user_id, payload, created_at) "
            "VALUES (:id, 'test', :et, :ec, 'test-record', 'test', :payload, NOW())"
        ),
        {"id": event_id, "et": test_event_type, "ec": entity_code,
         "payload": json.dumps(body.get("payload", {"test": True, "message": "Webhook test event"}))},
    )

    delivery_id = str(uuid.uuid4())
    db.execute(
        text(
            "INSERT INTO dbp_webhook_deliveries "
            "(id, webhook_id, event_id, status, attempts) "
            "VALUES (:id, :wid, :eid, 'pending', 0)"
        ),
        {"id": delivery_id, "wid": wh[0], "eid": event_id},
    )
    db.flush()

    import hashlib
    import hmac

    import httpx

    payload_data = body.get("payload", {"test": True, "message": "Webhook test event"})
    payload_str = json.dumps(payload_data)

    try:
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)

        if secret:
            sig = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
            req_headers["X-DBP-Signature"] = sig

        with httpx.Client(timeout=10) as client:
            resp = client.post(target_url, content=payload_str, headers=req_headers)
            success = resp.status_code < 400

        db.execute(
            text(
                "UPDATE dbp_webhook_deliveries "
                "SET status=:st, attempts=1, last_response_code=:code "
                "WHERE id = :did"
            ),
            {"did": delivery_id, "st": "success" if success else "failed",
             "code": resp.status_code},
        )

    except Exception as e:
        db.execute(
            text(
                "UPDATE dbp_webhook_deliveries "
                "SET status='failed', attempts=1, last_response_code=NULL, "
                "last_error=:err WHERE id = :did"
            ),
            {"did": delivery_id, "err": str(e)[:500]},
        )
        success = False

    db.commit()

    return {
        "status": "success",
        "data": {
            "delivery_id": delivery_id,
            "event_id": event_id,
            "test_result": "success" if success else "failed",
        },
    }


# ──────────────────────────────────────────────────────────────
# WEBHOOK HEALTH
# ──────────────────────────────────────────────────────────────

@router.get(
    "/webhooks/{webhook_code}/health",
    dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)],
)
async def webhook_health(
    webhook_code: str,
    hours: int | None=None,
    db: Session = Depends(get_db),
):
    """Get webhook delivery health metrics."""
    wh_id = _resolve_webhook_id(db, webhook_code)
    if not wh_id:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": "Webhook not found"},
        })

    health = db.execute(
        text(
            "SELECT "
            "COUNT(*) as total_deliveries, "
            "COUNT(*) FILTER (WHERE status='success') as success_count, "
            "COUNT(*) FILTER (WHERE status='failed') as failed_count, "
            "COUNT(*) FILTER (WHERE status='pending') as pending_count, "
            "COUNT(*) FILTER (WHERE status='retrying') as retrying_count, "
            "AVG(attempts) FILTER (WHERE status='success') as avg_success_attempts, "
            "MAX(attempts) as max_attempts, "
            "COUNT(DISTINCT event_id) as unique_events "
            "FROM dbp_webhook_deliveries "
            "WHERE webhook_id = :wid AND created_at >= NOW() - (:hrs || ' hours')::interval"
        ),
        {"wid": wh_id, "hrs": str(hours)},
    ).fetchone()

    error_breakdown = db.execute(
        text(
            "SELECT last_response_code, COUNT(*) as cnt "
            "FROM dbp_webhook_deliveries "
            "WHERE webhook_id = :wid AND status = 'failed' "
            "AND created_at >= NOW() - (:hrs || ' hours')::interval "
            "GROUP BY last_response_code "
            "ORDER BY cnt DESC"
        ),
        {"wid": wh_id, "hrs": str(hours)},
    ).fetchall()

    total = health[0] or 0
    success = health[1] or 0

    return {
        "status": "success",
        "data": {
            "webhook_code": webhook_code,
            "period_hours": hours,
            "total_deliveries": total,
            "success_count": success,
            "failed_count": health[2] or 0,
            "pending_count": health[3] or 0,
            "retrying_count": health[4] or 0,
            "success_rate": round(success / total * 100, 2) if total > 0 else 0,
            "avg_attempts_to_success": round(float(health[5]), 2) if health[5] else None,
            "max_attempts": health[6] or 0,
            "unique_events": health[7] or 0,
            "error_breakdown": [
                {"response_code": e[0], "count": e[1]}
                for e in error_breakdown
            ],
        },
    }
