from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from core.auth import require_permission, get_current_user
from core.rate_limit import read_limiter, write_limiter
from core.iot_engine import IoTEngine

router = APIRouter(prefix="/api/v1/dynamic/iot", tags=["IoT & Devices"])


@router.get("/devices", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_devices(device_type: str = None, status: str = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": IoTEngine(db).list_devices(user["tenant_id"], device_type=device_type, status=status)}


@router.post("/devices", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_device(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ["device_name", "device_type"]:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    did = IoTEngine(db).create_device(user["tenant_id"], body["device_name"], body["device_type"],
        device_model=body.get("device_model"), serial_number=body.get("serial_number"),
        firmware_version=body.get("firmware_version"), location=body.get("location"),
        metadata=body.get("metadata"))
    db.commit()
    return {"status": "success", "data": {"id": did, "message": "Device created"}}


@router.get("/devices/{device_id}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_device(device_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = IoTEngine(db).get_device(user["tenant_id"], device_id)
    if not data:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Device not found"}})
    return {"status": "success", "data": data}


@router.put("/devices/{device_id}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_device(device_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = IoTEngine(db).update_device(user["tenant_id"], device_id, **body)
    db.commit()
    return {"status": "success", "data": result}


@router.put("/devices/{device_id}/heartbeat", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def heartbeat(device_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = IoTEngine(db).heartbeat(user["tenant_id"], device_id)
    db.commit()
    return {"status": "success", "data": result}


@router.get("/telemetry", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_telemetry(device_id: str = None, metric_name: str = None, limit: int = 100,
                        user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": IoTEngine(db).get_telemetry(user["tenant_id"],
        device_id=device_id, metric_name=metric_name, limit=limit)}


@router.post("/telemetry", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def record_telemetry(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ["device_id", "metric_name", "metric_value"]:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    tid = IoTEngine(db).record_telemetry(user["tenant_id"], body["device_id"],
        body["metric_name"], body["metric_value"], unit=body.get("unit"),
        quality_score=body.get("quality_score", 1.0))
    db.commit()
    return {"status": "success", "data": {"id": tid, "message": "Telemetry recorded"}}


@router.get("/alerts", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_alerts(device_id: str = None, is_acknowledged: bool = None, severity: str = None,
                     user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": IoTEngine(db).list_alerts(user["tenant_id"],
        device_id=device_id, is_acknowledged=is_acknowledged, severity=severity)}


@router.post("/alerts", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_alert(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ["device_id", "alert_type", "severity"]:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    aid = IoTEngine(db).create_alert(user["tenant_id"], body["device_id"],
        body["alert_type"], body["severity"], message=body.get("message"))
    db.commit()
    return {"status": "success", "data": {"id": aid, "message": "Alert created"}}


@router.put("/alerts/{alert_id}/acknowledge", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def acknowledge_alert(alert_id: str, body: dict = {}, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = IoTEngine(db).acknowledge_alert(user["tenant_id"], alert_id, user.get("user_id"))
    db.commit()
    return {"status": "success", "data": result}


@router.get("/rules", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_rules(device_type: str = None, is_active: bool = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": IoTEngine(db).list_rules(user["tenant_id"], device_type=device_type, is_active=is_active)}


@router.post("/rules", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_rule(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ["rule_name", "condition_config", "action_config"]:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    rid = IoTEngine(db).create_rule(user["tenant_id"], body["rule_name"],
        body["condition_config"], body["action_config"], device_type=body.get("device_type"))
    db.commit()
    return {"status": "success", "data": {"id": rid, "message": "Rule created"}}


@router.put("/rules/{rule_id}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_rule(rule_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = IoTEngine(db).update_rule(user["tenant_id"], rule_id, **body)
    db.commit()
    return {"status": "success", "data": result}


@router.get("/firmware", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_firmware(device_type: str = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": IoTEngine(db).list_firmware(user["tenant_id"], device_type=device_type)}


@router.post("/firmware", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_firmware(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ["device_type", "version"]:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    fid = IoTEngine(db).create_firmware(user["tenant_id"], body["device_type"], body["version"],
        changelog=body.get("changelog"), download_url=body.get("download_url"),
        file_size_bytes=body.get("file_size_bytes"))
    db.commit()
    return {"status": "success", "data": {"id": fid, "message": "Firmware registered"}}
