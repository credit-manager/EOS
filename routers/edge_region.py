from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.edge_region import EdgeRegionEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic/edge", tags=["Edge & Multi-Region"])


# -------------------------------------------------- edge nodes
@router.get("/nodes",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_nodes(region: str | None = None, status: str | None = None,
                    user: dict | None=None, db: Session = Depends(get_db)):
    data = EdgeRegionEngine(db).list_nodes(region=region, status=status)
    return {"status": "success", "data": data}


@router.post("/nodes",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_node(body: dict,
                    user: dict | None=None, db: Session = Depends(get_db)):
    required = ["node_name", "region", "endpoint_url"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    nid = EdgeRegionEngine(db).create_node(
        body["node_name"], body["region"], body["endpoint_url"],
        metadata=body.get("metadata"))
    db.commit()
    return {"status": "success", "data": {"id": nid, "message": "Node created"}}


@router.get("/nodes/{node_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_node(node_id: str,
                 user: dict | None=None, db: Session = Depends(get_db)):
    data = EdgeRegionEngine(db).get_node(node_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Node not found"}})
    return {"status": "success", "data": data}


@router.put("/nodes/{node_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_node(node_id: str, body: dict,
                    user: dict | None=None, db: Session = Depends(get_db)):
    result = EdgeRegionEngine(db).update_node(node_id, **body)
    db.commit()
    return {"status": "success", "data": result}


# ------------------------------------------------ region configs
@router.get("/region-configs",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_region_configs(user: dict | None=None, db: Session = Depends(get_db)):
    data = EdgeRegionEngine(db).list_region_configs(user["tenant_id"])
    return {"status": "success", "data": data}


@router.post("/region-configs",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_region_config(body: dict,
                             user: dict | None=None, db: Session = Depends(get_db)):
    if "region" not in body:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "MISSING", "message": "region required"}})
    rid = EdgeRegionEngine(db).create_region_config(
        user["tenant_id"], body["region"],
        is_primary=body.get("is_primary", False),
        data_residency=body.get("data_residency"),
        replication_mode=body.get("replication_mode", "async"))
    db.commit()
    return {"status": "success", "data": {"id": rid, "message": "Region config created"}}


@router.put("/region-configs/{config_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_region_config(config_id: str, body: dict,
                             user: dict | None=None, db: Session = Depends(get_db)):
    result = EdgeRegionEngine(db).update_region_config(
        user["tenant_id"], config_id, **body)
    db.commit()
    return {"status": "success", "data": result}


# -------------------------------------------------- sync logs
@router.get("/sync-logs",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_sync_logs(node_id: str | None = None, status: str | None = None, limit: int = 50,
                        user: dict | None=None, db: Session = Depends(get_db)):
    data = EdgeRegionEngine(db).list_sync_logs(
        user["tenant_id"], node_id=node_id, status=status, limit=limit)
    return {"status": "success", "data": data}


@router.post("/sync-logs",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_sync_log(body: dict,
                        user: dict | None=None, db: Session = Depends(get_db)):
    required = ["node_id", "sync_type"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    sid = EdgeRegionEngine(db).create_sync_log(
        body["node_id"], user["tenant_id"], body["sync_type"],
        entity_type=body.get("entity_type"), entity_id=body.get("entity_id"))
    db.commit()
    return {"status": "success", "data": {"id": sid, "message": "Sync log created"}}


@router.put("/sync-logs/{sync_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_sync_log(sync_id: str, body: dict,
                        user: dict | None=None, db: Session = Depends(get_db)):
    if "status" not in body:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "MISSING", "message": "status required"}})
    result = EdgeRegionEngine(db).update_sync_log(sync_id, body["status"])
    db.commit()
    return {"status": "success", "data": result}


# ------------------------------------------------ network topology
@router.get("/topology",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_topology(node_id: str | None = None,
                       user: dict | None=None, db: Session = Depends(get_db)):
    data = EdgeRegionEngine(db).list_links(node_id=node_id)
    return {"status": "success", "data": data}


@router.post("/topology",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_link(body: dict,
                    user: dict | None=None, db: Session = Depends(get_db)):
    required = ["node_id", "peer_node_id"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    lid = EdgeRegionEngine(db).create_link(
        body["node_id"], body["peer_node_id"],
        link_type=body.get("link_type", "mesh"),
        bandwidth_mbps=body.get("bandwidth_mbps"))
    db.commit()
    return {"status": "success", "data": {"id": lid, "message": "Link created"}}


@router.put("/topology/{link_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_link(link_id: str, body: dict,
                    user: dict | None=None, db: Session = Depends(get_db)):
    if "is_active" not in body:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "MISSING", "message": "is_active required"}})
    result = EdgeRegionEngine(db).update_link(link_id, body["is_active"])
    db.commit()
    return {"status": "success", "data": result}


# -------------------------------------------------- failover
@router.get("/failovers",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_failovers(status: str | None = None,
                        user: dict | None=None, db: Session = Depends(get_db)):
    data = EdgeRegionEngine(db).list_failovers(user["tenant_id"], status=status)
    return {"status": "success", "data": data}


@router.post("/failovers",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_failover(body: dict,
                        user: dict | None=None, db: Session = Depends(get_db)):
    required = ["source_region", "target_region"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    fid = EdgeRegionEngine(db).create_failover(
        user["tenant_id"], body["source_region"], body["target_region"],
        trigger_reason=body.get("trigger_reason"))
    db.commit()
    return {"status": "success", "data": {"id": fid, "message": "Failover created"}}


@router.put("/failovers/{failover_id}/activate",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def activate_failover(failover_id: str,
                           user: dict | None=None, db: Session = Depends(get_db)):
    result = EdgeRegionEngine(db).activate_failover(user["tenant_id"], failover_id)
    db.commit()
    return {"status": "success", "data": result}
