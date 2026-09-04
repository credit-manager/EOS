from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.blockchain_engine import BlockchainEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic/blockchain", tags=["Blockchain & Immutable Audit"])


@router.get("/chains", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_chains(chain_type: str | None = None, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": BlockchainEngine(db).list_chains(user["tenant_id"], chain_type=chain_type)}


@router.post("/chains", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_chain(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    for f in ["chain_name", "chain_type"]:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    cid = BlockchainEngine(db).create_chain(user["tenant_id"], body["chain_name"], body["chain_type"],
        consensus=body.get("consensus"), node_count=body.get("node_count", 1), config=body.get("config"))
    db.commit()
    return {"status": "success", "data": {"id": cid, "message": "Chain created"}}


@router.get("/chains/{chain_id}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_chain(chain_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    data = BlockchainEngine(db).get_chain(user["tenant_id"], chain_id)
    if not data:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Chain not found"}})
    return {"status": "success", "data": data}


@router.get("/nodes", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_nodes(chain_id: str | None = None, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": BlockchainEngine(db).list_nodes(chain_id=chain_id)}


@router.post("/nodes", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_node(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    for f in ["chain_id", "node_name", "node_url"]:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    nid = BlockchainEngine(db).create_node(body["chain_id"], body["node_name"], body["node_url"],
        role=body.get("role", "follower"))
    db.commit()
    return {"status": "success", "data": {"id": nid, "message": "Node created"}}


@router.put("/nodes/{node_id}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_node(node_id: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    result = BlockchainEngine(db).update_node(node_id, **body)
    db.commit()
    return {"status": "success", "data": result}


@router.get("/records", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_records(entity_type: str | None = None, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": BlockchainEngine(db).list_records(user["tenant_id"], entity_type=entity_type)}


@router.post("/records", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def add_record(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    for f in ["entity_type", "entity_id", "content_hash", "chain_id"]:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    rid = BlockchainEngine(db).add_record(user["tenant_id"], body["entity_type"], body["entity_id"],
        body["content_hash"], previous_hash=body.get("previous_hash"),
        block_number=body.get("block_number", 0), chain_id=body["chain_id"],
        metadata=body.get("metadata"))
    db.commit()
    return {"status": "success", "data": {"id": rid, "message": "Record added"}}


@router.post("/records/{record_id}/verify", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def verify_record(record_id: str, body: dict | None = None, user: dict | None=None, db: Session = Depends(get_db)):
    if body is None:
        body = {}
    vid = BlockchainEngine(db).verify_record(user["tenant_id"], record_id,
        body.get("verification_result", True), verified_by=user.get("user_id"))
    db.commit()
    return {"status": "success", "data": {"id": vid, "message": "Record verified"}}


@router.get("/verifications", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_verifications(record_id: str | None = None, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": BlockchainEngine(db).list_verifications(user["tenant_id"], record_id=record_id)}


@router.get("/immutable-audit", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_immutable_audit(entity_type: str | None = None, entity_id: str | None = None,
                              user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": BlockchainEngine(db).list_immutable_audit(user["tenant_id"],
        entity_type=entity_type, entity_id=entity_id)}


@router.post("/immutable-audit", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def add_immutable_audit(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    for f in ["entity_type", "entity_id", "action"]:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    result = BlockchainEngine(db).add_immutable_audit(user["tenant_id"], body["entity_type"],
        body["entity_id"], body["action"], before_data=body.get("before_data"),
        after_data=body.get("after_data"), actor_id=user.get("user_id"))
    db.commit()
    return {"status": "success", "data": result}
