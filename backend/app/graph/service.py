from collections import defaultdict, deque
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..metadata.models import MetadataEntity
from ..records.models import Record

MAX_DEPTH = 3
_TITLE_CANDIDATES = ("name", "title", "label", "code", "number")


# ---------------------------------------------------------------------------
# Business Graph V2 - Core graph class
# ---------------------------------------------------------------------------

class BusinessGraph:
    """Business Graph V2 - In-memory graph representation with analytics"""

    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.edges: dict[str, list[dict]] = defaultdict(list)
        self.reverse_edges: dict[str, list[dict]] = defaultdict(list)

    def add_node(self, ref: str, data: dict) -> None:
        """Add a node to the graph"""
        self.nodes[ref] = data

    def add_edge(self, source: str, target: str, edge_data: dict) -> None:
        """Add a directed edge"""
        self.edges[source].append({"target": target, **edge_data})
        self.reverse_edges[target].append({"source": source, **edge_data})

    def get_node(self, ref: str) -> dict | None:
        """Get node by ref"""
        return self.nodes.get(ref)

    def get_neighbors(self, ref: str) -> list[str]:
        """Get all neighbors (outgoing)"""
        return [e["target"] for e in self.edges.get(ref, [])]

    def get_reverse_neighbors(self, ref: str) -> list[str]:
        """Get all reverse neighbors (incoming)"""
        return [e["source"] for e in self.reverse_edges.get(ref, [])]

    def node_count(self) -> int:
        """Get number of nodes"""
        return len(self.nodes)

    def edge_count(self) -> int:
        """Get number of edges"""
        return sum(len(edges) for edges in self.edges.values())


# ---------------------------------------------------------------------------
# Business Graph V2 - DFS
# ---------------------------------------------------------------------------

def dfs(
    graph: BusinessGraph,
    start: str,
    max_depth: int = MAX_DEPTH,
) -> list[str]:
    """Depth-first search from start node"""
    visited: set[str] = set()
    result: list[str] = []

    def _dfs(node: str, depth: int) -> None:
        if depth > max_depth or node in visited:
            return
        visited.add(node)
        result.append(node)
        for neighbor in graph.get_neighbors(node):
            _dfs(neighbor, depth + 1)

    _dfs(start, 0)
    return result


def dfs_with_data(
    graph: BusinessGraph,
    start: str,
    max_depth: int = MAX_DEPTH,
) -> dict:
    """DFS returning nodes with their data"""
    visited: set[str] = set()
    nodes: list[dict] = []
    edges: list[dict] = []

    def _dfs(node: str, depth: int) -> None:
        if depth > max_depth or node in visited:
            return
        visited.add(node)
        node_data = graph.get_node(node)
        if node_data:
            nodes.append({"ref": node, "depth": depth, **node_data})
        for edge in graph.edges.get(node, []):
            target = edge["target"]
            if target not in visited:
                edges.append({
                    "source": node,
                    "target": target,
                    "field": edge.get("field", ""),
                })
                _dfs(target, depth + 1)

    _dfs(start, 0)
    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# Business Graph V2 - BFS / Shortest Path
# ---------------------------------------------------------------------------

def bfs(
    graph: BusinessGraph,
    start: str,
    max_depth: int = MAX_DEPTH,
) -> list[str]:
    """Breadth-first search from start node"""
    visited: set[str] = {start}
    queue: deque[tuple[str, int]] = deque([(start, 0)])
    result: list[str] = []

    while queue:
        node, depth = queue.popleft()
        if depth > max_depth:
            continue
        result.append(node)
        for neighbor in graph.get_neighbors(node):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, depth + 1))

    return result


def shortest_path(
    graph: BusinessGraph,
    start: str,
    end: str,
    max_depth: int = MAX_DEPTH,
) -> list[str] | None:
    """Find shortest path between two nodes using BFS"""
    if start == end:
        return [start]

    visited: set[str] = {start}
    queue: deque[tuple[str, list[str]]] = deque([(start, [start])])

    while queue:
        node, path = queue.popleft()
        if len(path) > max_depth:
            continue

        for neighbor in graph.get_neighbors(node):
            if neighbor == end:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return None


def shortest_path_length(
    graph: BusinessGraph,
    start: str,
    end: str,
    max_depth: int = MAX_DEPTH,
) -> int | None:
    """Find shortest path length between two nodes"""
    path = shortest_path(graph, start, end, max_depth)
    return len(path) - 1 if path else None


# ---------------------------------------------------------------------------
# Business Graph V2 - Cycle Detection
# ---------------------------------------------------------------------------

def detect_cycles(graph: BusinessGraph) -> list[list[str]]:
    """Detect all cycles in the graph using DFS"""
    visited: set[str] = set()
    rec_stack: set[str] = set()
    cycles: list[list[str]] = []

    def _dfs(node: str, path: list[str]) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get_neighbors(node):
            if neighbor not in visited:
                _dfs(neighbor, path)
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)

        path.pop()
        rec_stack.remove(node)

    for node in graph.nodes:
        if node not in visited:
            _dfs(node, [])

    return cycles


# ---------------------------------------------------------------------------
# Business Graph V2 - Centrality Analysis
# ---------------------------------------------------------------------------

def degree_centrality(graph: BusinessGraph) -> dict[str, float]:
    """Calculate degree centrality for all nodes"""
    n = graph.node_count()
    if n <= 1:
        return {node: 0.0 for node in graph.nodes}

    centrality = {}
    for node in graph.nodes:
        out_degree = len(graph.get_neighbors(node))
        in_degree = len(graph.get_reverse_neighbors(node))
        centrality[node] = (out_degree + in_degree) / (n - 1)

    return centrality


def betweenness_centrality(graph: BusinessGraph) -> dict[str, float]:
    """Calculate betweenness centrality for all nodes"""
    n = graph.node_count()
    if n <= 1:
        return {node: 0.0 for node in graph.nodes}

    centrality = {node: 0.0 for node in graph.nodes}

    for s in graph.nodes:
        # BFS from s
        visited: set[str] = {s}
        queue: deque[tuple[str, list[str]]] = deque([(s, [s])])
        paths: list[list[str]] = []

        while queue:
            node, path = queue.popleft()
            for neighbor in graph.get_neighbors(node):
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = path + [neighbor]
                    queue.append((neighbor, new_path))
                    paths.append(new_path)

        # Count contributions
        for path in paths:
            for node in path[1:-1]:
                centrality[node] += 1.0

    # Normalize
    if n > 2:
        for node in centrality:
            centrality[node] /= (n - 1) * (n - 2)

    return centrality


def closeness_centrality(graph: BusinessGraph) -> dict[str, float]:
    """Calculate closeness centrality for all nodes"""
    centrality = {}

    for node in graph.nodes:
        total_distance = 0
        reachable = 0

        # BFS to calculate distances
        visited: set[str] = {node}
        queue: deque[tuple[str, int]] = deque([(node, 0)])

        while queue:
            current, distance = queue.popleft()
            if current != node:
                total_distance += distance
                reachable += 1

            for neighbor in graph.get_neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, distance + 1))

        if reachable > 0 and total_distance > 0:
            centrality[node] = (reachable - 1) / total_distance
        else:
            centrality[node] = 0.0

    return centrality


# ---------------------------------------------------------------------------
# Business Graph V2 - Impact Analysis
# ---------------------------------------------------------------------------

def impact_analysis(
    graph: BusinessGraph,
    node: str,
    max_depth: int = MAX_DEPTH,
) -> dict:
    """Analyze impact of changes to a node"""
    # Find all downstream nodes (what this node affects)
    downstream = bfs(graph, node, max_depth)
    downstream.remove(node)

    # Find all upstream nodes (what affects this node)
    visited: set[str] = {node}
    queue: deque[tuple[str, int]] = deque([(node, 0)])
    upstream: list[tuple[str, int]] = []

    while queue:
        current, depth = queue.popleft()
        for neighbor in graph.get_reverse_neighbors(current):
            if neighbor not in visited and depth + 1 <= max_depth:
                visited.add(neighbor)
                upstream.append((neighbor, depth + 1))
                queue.append((neighbor, depth + 1))

    # Calculate risk score based on number of affected nodes
    risk_score = min(1.0, (len(downstream) + len(upstream)) / 20.0)

    return {
        "node": node,
        "downstream_count": len(downstream),
        "downstream": downstream,
        "upstream_count": len(upstream),
        "upstream": [u[0] for u in upstream],
        "risk_score": risk_score,
        "risk_level": "high" if risk_score > 0.7 else "medium" if risk_score > 0.3 else "low",
    }


# ---------------------------------------------------------------------------
# Business Graph V2 - Health Analysis
# ---------------------------------------------------------------------------

def graph_health(graph: BusinessGraph) -> dict:
    """Analyze overall graph health"""
    node_count = graph.node_count()
    edge_count = graph.edge_count()

    # Check for cycles
    cycles = detect_cycles(graph)
    has_cycles = len(cycles) > 0

    # Calculate connectivity
    if node_count > 0:
        # Find connected components using BFS
        visited: set[str] = set()
        components = 0

        for node in graph.nodes:
            if node not in visited:
                components += 1
                queue: deque[str] = deque([node])
                while queue:
                    current = queue.popleft()
                    if current in visited:
                        continue
                    visited.add(current)
                    for neighbor in graph.get_neighbors(current):
                        if neighbor not in visited:
                            queue.append(neighbor)
                    for neighbor in graph.get_reverse_neighbors(current):
                        if neighbor not in visited:
                            queue.append(neighbor)

        connectivity = 1.0 - ((components - 1) / max(1, node_count - 1)) if node_count > 1 else 1.0
    else:
        connectivity = 0.0

    # Calculate density
    max_edges = node_count * (node_count - 1) if node_count > 1 else 1
    density = edge_count / max_edges if max_edges > 0 else 0.0

    # Overall health score
    health_score = (
        (1.0 if not has_cycles else 0.5) * 0.3 +
        connectivity * 0.4 +
        min(1.0, density * 10) * 0.3
    )

    return {
        "node_count": node_count,
        "edge_count": edge_count,
        "has_cycles": has_cycles,
        "cycle_count": len(cycles),
        "components": components if node_count > 0 else 0,
        "connectivity": round(connectivity, 3),
        "density": round(density, 3),
        "health_score": round(health_score, 3),
        "health_level": "good" if health_score > 0.7 else "fair" if health_score > 0.4 else "poor",
    }


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


def can_read(metadata: MetadataEntity, role: str) -> bool:
    if role == "admin":
        return True
    permissions = metadata.definition.get("permissions")
    if not isinstance(permissions, dict):
        return "read" in {"create", "read", "update", "delete"}
    return "read" in permissions.get("member", {"create", "read", "update", "delete"})


def _ref(entity_code: str, record_id: UUID) -> str:
    return f"{entity_code}:{record_id}"


def _title(record: Record, metadata: MetadataEntity) -> str:
    data = record.data or {}
    for code in _TITLE_CANDIDATES:
        value = data.get(code)
        if isinstance(value, str) and value:
            return value
    return f"{record.entity_code} / {str(record.id)[-8:]}"


def _summary(record: Record, metadata: MetadataEntity) -> dict:
    return {
        "ref": _ref(record.entity_code, record.id),
        "entity_code": record.entity_code,
        "record_id": record.id,
        "title": _title(record, metadata),
        "data": record.data or {},
    }


def relation_edges(metadata: MetadataEntity, data: dict) -> list[dict]:
    """Extract resolved relation references from a record's data dict."""
    edges: list[dict] = []
    for field in metadata.definition.get("fields", []):
        if field.get("type") != "relation":
            continue
        raw = data.get(field["code"])
        if not raw:
            continue
        try:
            target_id = UUID(str(raw))
        except (ValueError, TypeError):
            continue
        edges.append(
            {
                "field": field["code"],
                "target_entity": field["target_entity"],
                "target_id": str(target_id),
            }
        )
    return edges


def build_story(
    db: Session,
    *,
    tenant_id: UUID,
    role: str,
    entity_code: str,
    record_id: UUID,
    depth: int = 2,
) -> dict:
    depth = max(1, min(int(depth), MAX_DEPTH))

    root_metadata = _published(db, tenant_id, entity_code)
    if root_metadata is None or not can_read(root_metadata, role):
        raise HTTPException(status_code=404, detail="entity not found")
    root = db.scalar(
        select(Record).where(
            Record.tenant_id == tenant_id,
            Record.entity_code == entity_code,
            Record.id == record_id,
        )
    )
    if root is None:
        raise HTTPException(status_code=404, detail="record not found")

    nodes: list[dict] = []
    edges: list[dict] = []
    visited: set[tuple[str, UUID]] = set()
    queue: list[tuple[Record, str, int]] = [(root, entity_code, 0)]
    metadata_cache: dict[str, MetadataEntity] = {entity_code: root_metadata}
    record_cache: dict[tuple[str, UUID], Record] = {(entity_code, root.id): root}

    while queue:
        record, current_code, current_depth = queue.pop(0)
        key = (current_code, record.id)
        if key in visited:
            continue
        visited.add(key)
        metadata = metadata_cache.get(current_code)
        if metadata is None:
            metadata = _published(db, tenant_id, current_code)
            if metadata is None:
                continue
            metadata_cache[current_code] = metadata
        nodes.append(_summary(record, metadata))
        if current_depth >= depth:
            continue
        for field in metadata.definition.get("fields", []):
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
            target_metadata = _published(db, tenant_id, target_code)
            if target_metadata is None or not can_read(target_metadata, role):
                continue
            target_key = (target_code, target_id)
            target = record_cache.get(target_key)
            if target is None:
                target = db.scalar(
                    select(Record).where(
                        Record.tenant_id == tenant_id,
                        Record.entity_code == target_code,
                        Record.id == target_id,
                    )
                )
                if target is None:
                    continue
                record_cache[target_key] = target
            edges.append(
                {
                    "source": _ref(current_code, record.id),
                    "target": _ref(target_code, target_id),
                    "field": field["code"],
                    "target_entity": target_code,
                }
            )
            if target_key not in visited:
                queue.append((target, target_code, current_depth + 1))

    return {"root": _summary(root, root_metadata), "nodes": nodes, "edges": edges, "depth": depth}
