"""Business Graph Traversal — find paths, trace stories, map relationships."""

from collections import defaultdict, deque
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..metadata.models import MetadataEntity
from ..records.models import Record

_TITLE_CANDIDATES = ("name", "title", "label", "code", "number")
_MAX_DEPTH = 5


def _published(db: Session, tenant_id: UUID, entity_code: str) -> MetadataEntity | None:
    return db.scalar(
        select(MetadataEntity)
        .where(
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.code == entity_code,
            MetadataEntity.published_at.is_not(None),
        )
        .order_by(MetadataEntity.version.desc())
    )


def _all_published(db: Session, tenant_id: UUID) -> dict[str, MetadataEntity]:
    entities = db.scalars(
        select(MetadataEntity)
        .where(
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.published_at.is_not(None),
        )
        .order_by(MetadataEntity.version.desc())
    ).all()
    seen: set[str] = set()
    result: dict[str, MetadataEntity] = {}
    for e in entities:
        if e.code not in seen:
            seen.add(e.code)
            result[e.code] = e
    return result


def _title(record: Record, metadata: MetadataEntity | None) -> str:
    data = record.data or {}
    for code in _TITLE_CANDIDATES:
        value = data.get(code)
        if isinstance(value, str) and value:
            return value
    if metadata:
        return metadata.name or f"{record.entity_code} / {str(record.id)[-8:]}"
    return f"{record.entity_code} / {str(record.id)[-8:]}"


def _record_summary(record: Record, metadata: MetadataEntity | None) -> dict:
    return {
        "ref": f"{record.entity_code}:{record.id}",
        "entity_code": record.entity_code,
        "record_id": str(record.id),
        "title": _title(record, metadata),
        "data": record.data or {},
    }


# ---------------------------------------------------------------------------
# Entity Graph — knows all entity relationships for a tenant
# ---------------------------------------------------------------------------


class EntityGraph:
    """Represents the business graph for a tenant."""

    def __init__(self, db_session: Session, tenant_id: UUID):
        self.db = db_session
        self.tenant_id = tenant_id
        self._metadata: dict[str, MetadataEntity] = {}
        self._adjacency: dict[str, list[dict]] = defaultdict(list)
        self._reverse: dict[str, list[dict]] = defaultdict(list)
        self._built = False

    # -- construction --------------------------------------------------------

    def build(self) -> None:
        """Build the graph from metadata definitions (entity-level relationships)."""
        self._metadata = _all_published(self.db, self.tenant_id)

        for code, meta in self._metadata.items():
            fields = meta.definition.get("fields", [])
            for field in fields:
                if field.get("type") != "relation":
                    continue
                target = field.get("target_entity", "")
                if not target:
                    continue
                rel = {
                    "target": target,
                    "type": field.get("cardinality", "many_to_one"),
                    "fk": field["code"],
                    "field_code": field["code"],
                    "label": field.get("name", field["code"]),
                }
                self._adjacency[code].append(rel)
                self._reverse[target].append({
                    "source": code,
                    "type": field.get("cardinality", "many_to_one"),
                    "fk": field["code"],
                    "field_code": field["code"],
                    "label": field.get("name", field["code"]),
                })

        self._built = True

    def _ensure_built(self) -> None:
        if not self._built:
            self.build()

    # -- queries -------------------------------------------------------------

    def get_entity_codes(self) -> list[str]:
        """Return all known entity codes."""
        self._ensure_built()
        return list(self._metadata.keys())

    def get_metadata(self, entity_code: str) -> MetadataEntity | None:
        self._ensure_built()
        return self._metadata.get(entity_code)

    def get_neighbors(self, entity_code: str) -> list[dict]:
        """Get all connected entities (outgoing relationships)."""
        self._ensure_built()
        return list(self._adjacency.get(entity_code, []))

    def get_reverse_neighbors(self, entity_code: str) -> list[dict]:
        """Get all entities that reference this entity."""
        self._ensure_built()
        return list(self._reverse.get(entity_code, []))

    def find_path(
        self,
        from_entity: str,
        to_entity: str,
        max_depth: int = _MAX_DEPTH,
    ) -> list[dict] | None:
        """Find shortest path between two entity types using BFS.

        Returns a list of dicts describing the path, e.g.:
          [{"entity": "project", "via": "customer_id", "label": "Customer"}, ...]
        or None if no path exists.
        """
        self._ensure_built()

        if from_entity == to_entity:
            return [{"entity": from_entity, "via": None, "label": None}]

        visited: set[str] = {from_entity}
        queue: deque[tuple[str, list[dict]]] = deque([(from_entity, [])])

        while queue:
            current, path = queue.popleft()
            if len(path) >= max_depth:
                continue

            for rel in self._adjacency.get(current, []):
                target = rel["target"]
                if target == to_entity:
                    return path + [{
                        "entity": current,
                        "via": rel["fk"],
                        "label": rel["label"],
                    }, {
                        "entity": target,
                        "via": None,
                        "label": None,
                    }]
                if target not in visited:
                    visited.add(target)
                    queue.append((target, path + [{
                        "entity": current,
                        "via": rel["fk"],
                        "label": rel["label"],
                    }]))

        return None

    # -- record-level queries ------------------------------------------------

    def _resolve_record(
        self,
        entity_code: str,
        record_id: str,
    ) -> tuple[Record | None, MetadataEntity | None]:
        self._ensure_built()
        meta = self._metadata.get(entity_code)
        if meta is None:
            return None, None
        try:
            rid = UUID(record_id)
        except (ValueError, TypeError):
            return None, meta
        record = self.db.scalar(
            select(Record).where(
                Record.tenant_id == self.tenant_id,
                Record.entity_code == entity_code,
                Record.id == rid,
            )
        )
        return record, meta

    def get_related_records(
        self,
        entity_code: str,
        record_id: str,
        depth: int = 1,
    ) -> dict:
        """Get all related records for a specific entity instance (BFS)."""
        self._ensure_built()

        root_record, root_meta = self._resolve_record(entity_code, record_id)
        if root_record is None:
            return {"error": "record not found", "entity": entity_code, "record_id": record_id}

        nodes: list[dict] = []
        edges: list[dict] = []
        visited: set[tuple[str, UUID]] = set()
        queue: deque[tuple[Record, str, int]] = deque([(root_record, entity_code, 0)])
        metadata_cache: dict[str, MetadataEntity] = {entity_code: root_meta} if root_meta else {}
        record_cache: dict[tuple[str, UUID], Record] = {(entity_code, root_record.id): root_record}

        while queue:
            record, current_code, current_depth = queue.popleft()
            key = (current_code, record.id)
            if key in visited:
                continue
            visited.add(key)

            meta = metadata_cache.get(current_code)
            if meta is None:
                meta = _published(self.db, self.tenant_id, current_code)
                if meta is None:
                    continue
                metadata_cache[current_code] = meta

            nodes.append(_record_summary(record, meta))

            if current_depth >= depth:
                continue

            for field in meta.definition.get("fields", []):
                if field.get("type") != "relation":
                    continue
                raw = (record.data or {}).get(field["code"])
                if not raw:
                    continue
                try:
                    target_id = UUID(str(raw))
                except (ValueError, TypeError):
                    continue
                target_code = field["target_entity"]
                target_meta = metadata_cache.get(target_code)
                if target_meta is None:
                    target_meta = _published(self.db, self.tenant_id, target_code)
                    if target_meta is None:
                        continue
                    metadata_cache[target_code] = target_meta

                target_key = (target_code, target_id)
                target = record_cache.get(target_key)
                if target is None:
                    target = self.db.scalar(
                        select(Record).where(
                            Record.tenant_id == self.tenant_id,
                            Record.entity_code == target_code,
                            Record.id == target_id,
                        )
                    )
                    if target is None:
                        continue
                    record_cache[target_key] = target

                edges.append({
                    "source": f"{current_code}:{record.id}",
                    "target": f"{target_code}:{target_id}",
                    "field": field["code"],
                    "target_entity": target_code,
                    "label": field.get("name", field["code"]),
                })

                if target_key not in visited:
                    queue.append((target, target_code, current_depth + 1))

        return {
            "entity": entity_code,
            "record_id": record_id,
            "nodes": nodes,
            "edges": edges,
            "depth": depth,
            "total_related": len(nodes) - 1,
        }

    # -- entity story --------------------------------------------------------

    def get_entity_story(self, entity_code: str, record_id: str) -> dict:
        """Get the full business story for a record — all related data.

        Builds a structured narrative: customer info, contracts, financials,
        procurement, risks, timeline, and recent activity.
        """
        self._ensure_built()

        root_record, root_meta = self._resolve_record(entity_code, record_id)
        if root_record is None:
            return {"error": "record not found", "entity": entity_code, "record_id": record_id}

        data = root_record.data or {}

        story: dict = {
            "entity": entity_code,
            "record_id": record_id,
            "record": _record_summary(root_record, root_meta),
            "story": {},
        }

        # Collect all related records up to depth 3 for story building
        related = self.get_related_records(entity_code, record_id, depth=3)
        related_nodes = related.get("nodes", [])
        related_edges = related.get("edges", [])

        # Group related records by entity type
        by_entity: dict[str, list[dict]] = defaultdict(list)
        for node in related_nodes:
            if node["entity_code"] != entity_code or node["record_id"] != record_id:
                by_entity[node["entity_code"]].append(node)

        # Build story sections
        story["story"] = {
            "related_entities": dict(by_entity),
            "relationship_count": len(related_edges),
            "connections": [
                {
                    "from": e["source"],
                    "to": e["target"],
                    "via": e.get("label") or e.get("field", ""),
                    "target_entity": e.get("target_entity", ""),
                }
                for e in related_edges
            ],
            "direct_relations": by_entity,
            "summary": self._build_story_summary(entity_code, data, by_entity),
        }

        return story

    def _build_story_summary(
        self,
        entity_code: str,
        data: dict,
        related: dict[str, list[dict]],
    ) -> dict:
        """Build a high-level summary of the entity story."""
        summary: dict = {
            "entity_type": entity_code,
            "related_entity_count": len(related),
            "total_related_records": sum(len(v) for v in related.values()),
            "related_entity_types": list(related.keys()),
        }

        # Extract key financial fields if present
        financial_keys = ("budget", "total_budget", "value", "amount", "total_value",
                          "cost", "revenue", "total_spent", "price")
        financial_data: dict = {}
        for key in financial_keys:
            if key in data:
                financial_data[key] = data[key]
        if financial_data:
            summary["financial_overview"] = financial_data

        # Extract status/timeline fields
        status_keys = ("status", "phase", "state", "start_date", "end_date", "deadline")
        status_data: dict = {}
        for key in status_keys:
            if key in data:
                status_data[key] = data[key]
        if status_data:
            summary["status_overview"] = status_data

        return summary


# ---------------------------------------------------------------------------
# Graph Analytics — compute graph-level insights
# ---------------------------------------------------------------------------


class GraphAnalytics:
    """Compute analytics over the entity-level graph."""

    def __init__(self, entity_graph: EntityGraph):
        self.graph = entity_graph
        self.graph._ensure_built()

    def get_most_connected_entities(self) -> list[dict]:
        """Which entities have the most relationships?"""
        counts: dict[str, int] = {}
        for code in self.graph.get_entity_codes():
            outgoing = len(self.graph.get_neighbors(code))
            incoming = len(self.graph.get_reverse_neighbors(code))
            counts[code] = outgoing + incoming

        ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {
                "entity": code,
                "relationship_count": count,
                "outgoing": len(self.graph.get_neighbors(code)),
                "incoming": len(self.graph.get_reverse_neighbors(code)),
            }
            for code, count in ranked
            if count > 0
        ]

    def get_orphan_entities(self) -> list[str]:
        """Which entities have no relationships?"""
        orphans: list[str] = []
        for code in self.graph.get_entity_codes():
            if not self.graph.get_neighbors(code) and not self.graph.get_reverse_neighbors(code):
                orphans.append(code)
        return sorted(orphans)

    def get_financial_flow(
        self,
        from_entity: str,
        to_entity: str,
    ) -> dict:
        """Trace the financial flow between two entity types.

        Follows the path and summarizes value-carrying fields along the way.
        """
        path = self.graph.find_path(from_entity, to_entity)
        if path is None:
            return {
                "found": False,
                "from": from_entity,
                "to": to_entity,
                "path": None,
                "flow": [],
            }

        flow: list[dict] = []
        value_keywords = ("value", "amount", "budget", "price", "cost", "revenue", "total")

        for step in path:
            code = step["entity"]
            meta = self.graph.get_metadata(code)
            value_fields: list[str] = []
            if meta:
                for field in meta.definition.get("fields", []):
                    field_code = field.get("code", "")
                    field_type = field.get("type", "")
                    if field_type in ("number", "currency") or any(kw in field_code.lower() for kw in value_keywords):
                        value_fields.append(field_code)

            flow.append({
                "entity": code,
                "via": step.get("via"),
                "label": step.get("label"),
                "value_fields": value_fields,
            })

        return {
            "found": True,
            "from": from_entity,
            "to": to_entity,
            "path": [s["entity"] for s in path],
            "path_length": len(path) - 1,
            "flow": flow,
        }

    def get_graph_map(self) -> dict:
        """Return the full entity graph map."""
        nodes: list[dict] = []
        for code in self.graph.get_entity_codes():
            meta = self.graph.get_metadata(code)
            nodes.append({
                "entity": code,
                "name": meta.name if meta else code,
                "outgoing": len(self.graph.get_neighbors(code)),
                "incoming": len(self.graph.get_reverse_neighbors(code)),
            })

        edges: list[dict] = []
        seen: set[tuple[str, str]] = set()
        for code in self.graph.get_entity_codes():
            for rel in self.graph.get_neighbors(code):
                target = rel["target"]
                edge_key = (code, target)
                if edge_key not in seen:
                    seen.add(edge_key)
                    edges.append({
                        "source": code,
                        "target": target,
                        "type": rel.get("type", ""),
                        "field": rel.get("fk", ""),
                        "label": rel.get("label", ""),
                    })

        orphans = self.get_orphan_entities()
        most_connected = self.get_most_connected_entities()

        return {
            "entity_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
            "orphan_entities": orphans,
            "most_connected": most_connected[:10],
        }
