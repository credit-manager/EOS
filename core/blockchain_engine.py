"""
P49 Blockchain & Immutable Audit Trail Engine
"""
import uuid, hashlib, json
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text


class BlockchainEngine:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------- chains
    def create_chain(self, tenant_id, chain_name, chain_type, consensus=None,
                     node_count=1, config=None):
        cid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_blockchain_chains "
            "(id, tenant_id, chain_name, chain_type, consensus, node_count, config, created_at) "
            "VALUES (:id,:tid,:cn,:ct,:co,:nc,:cf,NOW())"
        ), {"id": cid, "tid": tenant_id, "cn": chain_name,
            "ct": chain_type, "co": consensus, "nc": node_count,
            "cf": json.dumps(config) if config else None})
        return cid

    def list_chains(self, tenant_id, chain_type=None):
        q = "SELECT id, chain_name, chain_type, consensus, node_count, status, created_at FROM dbp_blockchain_chains WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if chain_type:
            q += " AND chain_type=:ct"
            params["ct"] = chain_type
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "chain_name": r[1], "chain_type": r[2],
                 "consensus": r[3], "node_count": r[4],
                 "status": r[5],
                 "created_at": str(r[6]) if r[6] else None} for r in rows]

    def get_chain(self, tenant_id, chain_id):
        r = self.db.execute(text(
            "SELECT id, chain_name, chain_type, consensus, node_count, status, config, created_at "
            "FROM dbp_blockchain_chains WHERE id=:id AND tenant_id=:tid"
        ), {"id": chain_id, "tid": tenant_id}).fetchone()
        if not r:
            return None
        return {"id": r[0], "chain_name": r[1], "chain_type": r[2],
                "consensus": r[3], "node_count": r[4],
                "status": r[5], "config": r[6],
                "created_at": str(r[7]) if r[7] else None}

    # -------------------------------------------------- nodes
    def create_node(self, chain_id, node_name, node_url, role="follower"):
        nid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_blockchain_nodes "
            "(id, chain_id, node_name, node_url, role, status, created_at) "
            "VALUES (:id,:ci,:nn,:nu,:ro,'active',NOW())"
        ), {"id": nid, "ci": chain_id, "nn": node_name,
            "nu": node_url, "ro": role})
        return nid

    def list_nodes(self, chain_id=None):
        q = "SELECT id, chain_id, node_name, node_url, role, status, last_sync_at FROM dbp_blockchain_nodes"
        params: Dict[str, Any] = {}
        if chain_id:
            q += " WHERE chain_id=:ci"
            params["ci"] = chain_id
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "chain_id": r[1], "node_name": r[2],
                 "node_url": r[3], "role": r[4], "status": r[5],
                 "last_sync_at": str(r[6]) if r[6] else None} for r in rows]

    def update_node(self, node_id, **kwargs):
        if not kwargs:
            return None
        sets = [f"{k}=:{k}" for k in kwargs]
        params = {"id": node_id, **kwargs}
        self.db.execute(text(
            f"UPDATE dbp_blockchain_nodes SET {', '.join(sets)} WHERE id=:id"
        ), params)
        return {"id": node_id, "updated": True}

    # -------------------------------------------------- records
    def add_record(self, tenant_id, entity_type, entity_id, content_hash,
                   previous_hash=None, block_number=0, chain_id=None,
                   metadata=None):
        rid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_blockchain_records "
            "(id, tenant_id, entity_type, entity_id, content_hash, previous_hash, block_number, chain_id, metadata, recorded_at) "
            "VALUES (:id,:tid,:et,:ei,:ch,:ph,:bn,:ci,:md,NOW())"
        ), {"id": rid, "tid": tenant_id, "et": entity_type,
            "ei": entity_id, "ch": content_hash,
            "ph": previous_hash, "bn": block_number,
            "ci": chain_id,
            "md": json.dumps(metadata) if metadata else None})
        return rid

    def verify_record(self, tenant_id, record_id, verification_result,
                      verified_by=None):
        vid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_blockchain_verification "
            "(id, tenant_id, record_id, verification_result, verified_by, verified_at) "
            "VALUES (:id,:tid,:ri,:vr,:va,NOW())"
        ), {"id": vid, "tid": tenant_id, "ri": record_id,
            "vr": verification_result, "va": verified_by})
        return vid

    def list_records(self, tenant_id, entity_type=None, limit=50):
        q = "SELECT id, entity_type, entity_id, content_hash, previous_hash, block_number, chain_id, recorded_at FROM dbp_blockchain_records WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if entity_type:
            q += " AND entity_type=:et"
            params["et"] = entity_type
        q += " ORDER BY recorded_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "entity_type": r[1], "entity_id": r[2],
                 "content_hash": r[3], "previous_hash": r[4],
                 "block_number": r[5], "chain_id": r[6],
                 "recorded_at": str(r[7]) if r[7] else None} for r in rows]

    def list_verifications(self, tenant_id, record_id=None):
        q = "SELECT id, record_id, verification_result, verified_by, verified_at FROM dbp_blockchain_verification WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if record_id:
            q += " AND record_id=:ri"
            params["ri"] = record_id
        q += " ORDER BY verified_at DESC LIMIT 50"
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "record_id": r[1],
                 "verification_result": r[2],
                 "verified_by": r[3],
                 "verified_at": str(r[4]) if r[4] else None} for r in rows]

    # -------------------------------------------------- immutable audit
    def add_immutable_audit(self, tenant_id, entity_type, entity_id, action,
                            before_data=None, after_data=None, actor_id=None):
        aid = str(uuid.uuid4())
        content = f"{entity_type}:{entity_id}:{action}:{json.dumps(after_data, default=str)}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        self.db.execute(text(
            "INSERT INTO dbp_immutable_audit "
            "(id, tenant_id, entity_type, entity_id, action, actor_id, before_data, after_data, content_hash, created_at) "
            "VALUES (:id,:tid,:et,:ei,:ac,:ai,:bd,:ad,:ch,NOW())"
        ), {"id": aid, "tid": tenant_id, "et": entity_type,
            "ei": entity_id, "ac": action, "ai": actor_id,
            "bd": json.dumps(before_data, default=str) if before_data else None,
            "ad": json.dumps(after_data, default=str) if after_data else None,
            "ch": content_hash})
        return {"id": aid, "content_hash": content_hash}

    def list_immutable_audit(self, tenant_id, entity_type=None, entity_id=None,
                             limit=50):
        q = "SELECT id, entity_type, entity_id, action, actor_id, content_hash, created_at FROM dbp_immutable_audit WHERE tenant_id=:tid"
        params: Dict[str, Any] = {"tid": tenant_id}
        if entity_type:
            q += " AND entity_type=:et"
            params["et"] = entity_type
        if entity_id:
            q += " AND entity_id=:ei"
            params["ei"] = entity_id
        q += " ORDER BY created_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "entity_type": r[1], "entity_id": r[2],
                 "action": r[3], "actor_id": r[4],
                 "content_hash": r[5],
                 "created_at": str(r[6]) if r[6] else None} for r in rows]
