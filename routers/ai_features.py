from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
from core.auth import require_permission, get_current_user
from core.rate_limit import read_limiter, write_limiter
from core.ai_engine import AIEngine

router = APIRouter(prefix="/api/v1/dynamic", tags=["AI Features"])


# ------------------------------------------------------------------ models
@router.get("/companies/{cid}/ai-models",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_models(cid: str, model_type: str = None,
                     user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = AIEngine(db).list_models(cid, tenant_id=user["tenant_id"], model_type=model_type)
    return {"status": "success", "data": data}


@router.post("/companies/{cid}/ai-models",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_model(cid: str, body: dict,
                      user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    required = ["name", "model_type", "target_entity"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    eng = AIEngine(db)
    mid = eng.create_model(
        user["tenant_id"], cid, body["name"], body["model_type"], body["target_entity"],
        config=body.get("config"),
        status=body.get("status", "ready"),
        accuracy_score=body.get("accuracy_score"))
    db.commit()
    return {"status": "success", "data": {"id": mid, "message": "Model created"}}


@router.get("/ai-models/{mid}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_model(mid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    model = AIEngine(db).get_model(mid, user["tenant_id"])
    if not model:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Model not found"}})
    return {"status": "success", "data": model}


@router.put("/ai-models/{mid}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_model(mid: str, body: dict,
                      user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    eng = AIEngine(db)
    existing = eng.get_model(mid, user["tenant_id"])
    if not existing:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Model not found"}})
    kw = {k: v for k, v in body.items() if v is not None}
    result = eng.update_model(mid, user["tenant_id"], **kw)
    db.commit()
    return {"status": "success", "data": result}


# ------------------------------------------------------------------ predictions
@router.get("/companies/{cid}/ai-predictions",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_predictions(cid: str, model_id: str = None, entity_type: str = None,
                          status: str = None,
                          user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = AIEngine(db).list_predictions(
        cid, tenant_id=user["tenant_id"], model_id=model_id,
        entity_type=entity_type, status=status)
    return {"status": "success", "data": data}


@router.post("/companies/{cid}/ai-predictions",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_prediction(cid: str, body: dict,
                           user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    required = ["model_id", "prediction_type", "predicted_value"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    eng = AIEngine(db)
    if not eng.get_model(body["model_id"], user["tenant_id"]):
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "BAD_REQUEST", "message": "Invalid model_id"}})
    pid = eng.create_prediction(
        user["tenant_id"], cid, body["model_id"], body["prediction_type"],
        body["predicted_value"],
        entity_type=body.get("entity_type"),
        entity_id=body.get("entity_id"),
        confidence=body.get("confidence"),
        status=body.get("status", "pending"),
        expires_at=body.get("expires_at"))
    db.commit()
    return {"status": "success", "data": {"id": pid, "message": "Prediction created"}}


@router.get("/ai-predictions/{pid}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_prediction(pid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    pred = AIEngine(db).get_prediction(pid, user["tenant_id"])
    if not pred:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Prediction not found"}})
    return {"status": "success", "data": pred}


@router.post("/ai-predictions/{pid}/acknowledge",
             dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def acknowledge_prediction(pid: str, body: dict,
                                user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if "actual_value" not in body:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "MISSING", "message": "actual_value required"}})
    eng = AIEngine(db)
    pred = eng.get_prediction(pid, user["tenant_id"])
    if not pred:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Prediction not found"}})
    result = eng.acknowledge_prediction(pid, body["actual_value"], user["tenant_id"])
    db.commit()
    return {"status": "success", "data": result}


# ------------------------------------------------------------------ recommendations
@router.get("/companies/{cid}/ai-recommendations",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_recommendations(cid: str, status: str = None, priority: str = None,
                              user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = AIEngine(db).list_recommendations(
        cid, tenant_id=user["tenant_id"], status=status, priority=priority)
    return {"status": "success", "data": data}


@router.post("/companies/{cid}/ai-recommendations",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_recommendation(cid: str, body: dict,
                               user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    required = ["recommendation_type", "title", "description"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    eng = AIEngine(db)
    rid = eng.create_recommendation(
        user["tenant_id"], cid, body["recommendation_type"], body["title"],
        body["description"],
        entity_type=body.get("entity_type"),
        entity_id=body.get("entity_id"),
        priority=body.get("priority", "medium"),
        impact_score=body.get("impact_score"))
    db.commit()
    return {"status": "success", "data": {"id": rid, "message": "Recommendation created"}}


@router.post("/ai-recommendations/{rid}/acknowledge",
             dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def acknowledge_recommendation(rid: str, user: dict = Depends(get_current_user),
                                    db: Session = Depends(get_db)):
    eng = AIEngine(db)
    row = db.execute(
        text("SELECT id FROM dbp_ai_recommendations WHERE id=:id AND tenant_id=:t"), {"id": rid, "t": user["tenant_id"]}
    ).first()
    if not row:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Recommendation not found"}})
    result = eng.acknowledge_recommendation(rid, user.get("sub", "user"), user["tenant_id"])
    db.commit()
    return {"status": "success", "data": result}


# ------------------------------------------------------------------ anomalies
@router.get("/companies/{cid}/ai-anomalies",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_anomalies(cid: str, status: str = None, severity: str = None,
                        user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = AIEngine(db).list_anomalies(
        cid, tenant_id=user["tenant_id"], status=status, severity=severity)
    return {"status": "success", "data": data}


@router.post("/companies/{cid}/ai-anomalies",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_anomaly(cid: str, body: dict,
                        user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    required = ["entity_type", "metric_name", "expected_value", "actual_value"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    eng = AIEngine(db)
    aid = eng.create_anomaly(
        user["tenant_id"], cid, body["entity_type"], body["metric_name"],
        body["expected_value"], body["actual_value"],
        entity_id=body.get("entity_id"),
        severity=body.get("severity", "medium"))
    db.commit()
    return {"status": "success", "data": {"id": aid, "message": "Anomaly created"}}


@router.post("/ai-anomalies/{aid}/resolve",
             dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def resolve_anomaly(aid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    eng = AIEngine(db)
    row = db.execute(
        text("SELECT id FROM dbp_ai_anomalies WHERE id=:id AND tenant_id=:t"), {"id": aid, "t": user["tenant_id"]}
    ).first()
    if not row:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Anomaly not found"}})
    result = eng.resolve_anomaly(aid, user.get("sub", "user"), user["tenant_id"])
    db.commit()
    return {"status": "success", "data": result}


# ------------------------------------------------------------------ insights
@router.get("/companies/{cid}/ai-insights",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_insights(cid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = AIEngine(db).get_insights(cid, tenant_id=user["tenant_id"])
    return {"status": "success", "data": data}
