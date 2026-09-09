"""
P44 Multi-Region & Edge Deployment Engine
"""
import uuid, json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text


class EdgeRegionEngine:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------- edge nodes
    def create_node(self, node_name, region, endpoint_url, metadata=None):
        nid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_edge_nodes (id, node_name, region, endpoint_url, status, metadata, created_at) "
            "VALUES (:id,:nr,:re,:eu,'active',:md,NOW())"
        ), {"id": nid, "nr": node_name, "re": region, "eu": endpoint_url,
            "md": json.dumps(metadata) if metadata else None})
        return nid

    def list_nodes(self, region=None, status=None):
        q = "SELECT id, node_name, region, endpoint_url, status, latency_ms, capacity_pct, created_at FROM dbp_edge_nodes"
        conds, params = [], {}
        if region:
            conds.append("region=:re")
            params["re"] = region
        if status:
            conds.append("status=:st")
            params["st"] = status
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY created_at DESC"
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "node_name": r[1], "region": r[2],
                 "endpoint_url": r[3], "status": r[4], "latency_ms": r[5],
                 "capacity_pct": r[6], "created_at": str(r[7]) if r[7] else None}
                for r in rows]

    def update_node(self, node_id, **kwargs):
        if not kwargs:
            return None
        sets = [f"{k}=:{k}" for k in kwargs]
        params = {"id": node_id, **kwargs}
        self.db.execute(text(f"UPDATE dbp_edge_nodes SET {', '.join(sets)} WHERE id=:id"), params)
        return {"id": node_id, "updated": True}

    def get_node(self, node_id):
        r = self.db.execute(text(
            "SELECT id, node_name, region, endpoint_url, status, latency_ms, capacity_pct, created_at "
            "FROM dbp_edge_nodes WHERE id=:id"
        ), {"id": node_id}).fetchone()
        if not r:
            return None
        return {"id": r[0], "node_name": r[1], "region": r[2],
                "endpoint_url": r[3], "status": r[4], "latency_ms": r[5],
                "capacity_pct": r[6], "created_at": str(r[7]) if r[7] else None}

    # ------------------------------------------------ region configs
    def create_region_config(self, tenant_id, region, is_primary=False,
                             data_residency=None, replication_mode="async"):
        rid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_region_configs "
            "(id, tenant_id, region, is_primary, data_residency, replication_mode, status, created_at) "
            "VALUES (:id,:tid,:rg,:ip,:dr,:rm,'active',NOW())"
        ), {"id": rid, "tid": tenant_id, "rg": region, "ip": is_primary,
            "dr": data_residency, "rm": replication_mode})
        return rid

    def list_region_configs(self, tenant_id):
        rows = self.db.execute(text(
            "SELECT id, region, is_primary, data_residency, replication_mode, status, created_at "
            "FROM dbp_region_configs WHERE tenant_id=:tid ORDER BY created_at"
        ), {"tid": tenant_id}).fetchall()
        return [{"id": r[0], "region": r[1], "is_primary": r[2],
                 "data_residency": r[3], "replication_mode": r[4],
                 "status": r[5], "created_at": str(r[6]) if r[6] else None}
                for r in rows]

    def update_region_config(self, tenant_id, config_id, **kwargs):
        if not kwargs:
            return None
        sets = [f"{k}=:{k}" for k in kwargs]
        params = {"id": config_id, "tid": tenant_id, **kwargs}
        self.db.execute(text(
            f"UPDATE dbp_region_configs SET {', '.join(sets)} WHERE id=:id AND tenant_id=:tid"
        ), params)
        return {"id": config_id, "updated": True}

    # -------------------------------------------------- sync logs
    def create_sync_log(self, node_id, tenant_id, sync_type, entity_type=None,
                        entity_id=None):
        sid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_edge_sync_log "
            "(id, node_id, tenant_id, sync_type, entity_type, entity_id, status, created_at) "
            "VALUES (:id,:ni,:ti,:st,:et,:ei,'pending',NOW())"
        ), {"id": sid, "ni": node_id, "ti": tenant_id, "st": sync_type,
            "et": entity_type, "ei": entity_id})
        return sid

    def update_sync_log(self, sync_id, status):
        sets = ["status=:st"]
        params: Dict[str, Any] = {"id": sync_id, "st": status}
        if status in ("completed", "failed"):
            sets.append("completed_at=NOW()")
        self.db.execute(text(f"UPDATE dbp_edge_sync_log SET {', '.join(sets)} WHERE id=:id"), params)
        return {"id": sync_id, "status": status}

    def list_sync_logs(self, tenant_id, node_id=None, status=None, limit=50):
        q = "SELECT id, node_id, sync_type, entity_type, entity_id, status, retry_count, created_at, completed_at FROM dbp_edge_sync_log WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if node_id:
            q += " AND node_id=:ni"
            params["ni"] = node_id
        if status:
            q += " AND status=:st"
            params["st"] = status
        q += " ORDER BY created_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "node_id": r[1], "sync_type": r[2],
                 "entity_type": r[3], "entity_id": r[4], "status": r[5],
                 "retry_count": r[6],
                 "created_at": str(r[7]) if r[7] else None,
                 "completed_at": str(r[8]) if r[8] else None}
                for r in rows]

    # ------------------------------------------------ network topology
    def create_link(self, node_id, peer_node_id, link_type="mesh", bandwidth_mbps=None):
        lid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_network_topology "
            "(id, node_id, peer_node_id, link_type, bandwidth_mbps, is_active, created_at) "
            "VALUES (:id,:ni,:pi,:lt,:bm,true,NOW())"
        ), {"id": lid, "ni": node_id, "pi": peer_node_id, "lt": link_type,
            "bm": bandwidth_mbps})
        return lid

    def list_links(self, node_id=None):
        q = "SELECT id, node_id, peer_node_id, link_type, bandwidth_mbps, is_active FROM dbp_network_topology"
        params: Dict[str, Any] = {}
        if node_id:
            q += " WHERE node_id=:ni"
            params["ni"] = node_id
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "node_id": r[1], "peer_node_id": r[2],
                 "link_type": r[3], "bandwidth_mbps": r[4], "is_active": r[5]}
                for r in rows]

    def update_link(self, link_id, is_active):
        self.db.execute(text(
            "UPDATE dbp_network_topology SET is_active=:a WHERE id=:id"
        ), {"a": is_active, "id": link_id})
        return {"id": link_id, "is_active": is_active}

    # -------------------------------------------------- failover
    def create_failover(self, tenant_id, source_region, target_region,
                        trigger_reason=None):
        fid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_region_failover "
            "(id, tenant_id, source_region, target_region, trigger_reason, status, created_at) "
            "VALUES (:id,:tid,:sr,:tr,:rr,'pending',NOW())"
        ), {"id": fid, "tid": tenant_id, "sr": source_region,
            "tr": target_region, "rr": trigger_reason})
        return fid

    def activate_failover(self, tenant_id, failover_id):
        self.db.execute(text(
            "UPDATE dbp_region_failover SET status='active', activated_at=NOW() "
            "WHERE id=:id AND tenant_id=:tid"
        ), {"id": failover_id, "tid": tenant_id})
        return {"id": failover_id, "status": "active"}

    def list_failovers(self, tenant_id, status=None):
        q = "SELECT id, source_region, target_region, trigger_reason, status, activated_at, created_at FROM dbp_region_failover WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if status:
            q += " AND status=:st"
            params["st"] = status
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "source_region": r[1], "target_region": r[2],
                 "trigger_reason": r[3], "status": r[4],
                 "activated_at": str(r[5]) if r[5] else None,
                 "created_at": str(r[6]) if r[6] else None}
                for r in rows]
