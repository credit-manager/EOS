from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..metadata.models import MetadataEntity
from ..records.models import Record
from ..tenant import require_tenant
from .schemas import GraphStory
from .service import (
    BusinessGraph,
    betweenness_centrality,
    build_story,
    closeness_centrality,
    degree_centrality,
    detect_cycles,
    dfs,
    dfs_with_data,
    graph_health,
    impact_analysis,
    shortest_path,
)
from .traversal import EntityGraph, GraphAnalytics

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


# ---------------------------------------------------------------------------
# Business Graph V2 - Request/Response schemas
# ---------------------------------------------------------------------------

class DFSRequest(BaseModel):
    start_ref: str = Field(min_length=1, max_length=200)
    max_depth: int = Field(default=3, ge=1, le=10)


class DFSResponse(BaseModel):
    nodes: list[str]
    count: int


class ShortestPathRequest(BaseModel):
    start_ref: str = Field(min_length=1, max_length=200)
    end_ref: str = Field(min_length=1, max_length=200)
    max_depth: int = Field(default=10, ge=1, le=20)


class ShortestPathResponse(BaseModel):
    path: list[str] | None
    length: int | None
    found: bool


class ImpactAnalysisResponse(BaseModel):
    node: str
    downstream_count: int
    downstream: list[str]
    upstream_count: int
    upstream: list[str]
    risk_score: float
    risk_level: str


class GraphHealthResponse(BaseModel):
    node_count: int
    edge_count: int
    has_cycles: bool
    cycle_count: int
    components: int
    connectivity: float
    density: float
    health_score: float
    health_level: str


class CentralityResponse(BaseModel):
    degree: dict[str, float]
    betweenness: dict[str, float]
    closeness: dict[str, float]


class CyclesResponse(BaseModel):
    has_cycles: bool
    cycles: list[list[str]]
    count: int


# ---------------------------------------------------------------------------
# Business Graph V2 - Helper to build graph from story
# ---------------------------------------------------------------------------

def _build_graph_from_story(story: dict) -> BusinessGraph:
    """Build a BusinessGraph from a story dict"""
    graph = BusinessGraph()

    for node in story.get("nodes", []):
        ref = node.get("ref", "")
        if ref:
            graph.add_node(ref, node)

    for edge in story.get("edges", []):
        source = edge.get("source", "")
        target = edge.get("target", "")
        if source and target:
            graph.add_edge(source, target, edge)

    return graph


# ---------------------------------------------------------------------------
# Business Graph V2 - Endpoints
# ---------------------------------------------------------------------------

@router.get("/{entity_code}/{record_id}", response_model=GraphStory)
def get_story(
    entity_code: str,
    record_id: UUID,
    request: Request,
    depth: int = Query(default=2, ge=1, le=3),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> GraphStory:
    return GraphStory(
        **build_story(
            db,
            tenant_id=tenant_id,
            role=request.state.role,
            entity_code=entity_code,
            record_id=record_id,
            depth=depth,
        )
    )


@router.post("/dfs", response_model=DFSResponse)
def depth_first_search(
    payload: DFSRequest,
    request: Request,
    entity_code: str = Query(..., min_length=1, max_length=100),
    record_id: UUID = Query(...),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> DFSResponse:
    """Perform DFS from a record"""
    story = build_story(
        db,
        tenant_id=tenant_id,
        role=request.state.role,
        entity_code=entity_code,
        record_id=record_id,
        depth=payload.max_depth,
    )
    graph = _build_graph_from_story(story)
    nodes = dfs(graph, payload.start_ref, payload.max_depth)
    return DFSResponse(nodes=nodes, count=len(nodes))


@router.post("/dfs/data")
def depth_first_search_with_data(
    payload: DFSRequest,
    request: Request,
    entity_code: str = Query(..., min_length=1, max_length=100),
    record_id: UUID = Query(...),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    """Perform DFS from a record, returning nodes with data"""
    story = build_story(
        db,
        tenant_id=tenant_id,
        role=request.state.role,
        entity_code=entity_code,
        record_id=record_id,
        depth=payload.max_depth,
    )
    graph = _build_graph_from_story(story)
    return dfs_with_data(graph, payload.start_ref, payload.max_depth)


@router.post("/shortest-path", response_model=ShortestPathResponse)
def find_shortest_path(
    payload: ShortestPathRequest,
    request: Request,
    entity_code: str = Query(..., min_length=1, max_length=100),
    record_id: UUID = Query(...),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> ShortestPathResponse:
    """Find shortest path between two records"""
    story = build_story(
        db,
        tenant_id=tenant_id,
        role=request.state.role,
        entity_code=entity_code,
        record_id=record_id,
        depth=payload.max_depth,
    )
    graph = _build_graph_from_story(story)
    path = shortest_path(graph, payload.start_ref, payload.end_ref, payload.max_depth)
    return ShortestPathResponse(
        path=path,
        length=len(path) - 1 if path else None,
        found=path is not None,
    )


@router.post("/impact/{node_ref}", response_model=ImpactAnalysisResponse)
def analyze_impact(
    node_ref: str,
    request: Request,
    entity_code: str = Query(..., min_length=1, max_length=100),
    record_id: UUID = Query(...),
    max_depth: int = Query(default=3, ge=1, le=10),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> ImpactAnalysisResponse:
    """Analyze impact of changes to a node"""
    story = build_story(
        db,
        tenant_id=tenant_id,
        role=request.state.role,
        entity_code=entity_code,
        record_id=record_id,
        depth=max_depth,
    )
    graph = _build_graph_from_story(story)
    result = impact_analysis(graph, node_ref, max_depth)
    return ImpactAnalysisResponse(**result)


@router.get("/health/{entity_code}/{record_id}", response_model=GraphHealthResponse)
def get_graph_health(
    entity_code: str,
    record_id: UUID,
    request: Request,
    depth: int = Query(default=3, ge=1, le=10),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> GraphHealthResponse:
    """Get overall graph health"""
    story = build_story(
        db,
        tenant_id=tenant_id,
        role=request.state.role,
        entity_code=entity_code,
        record_id=record_id,
        depth=depth,
    )
    graph = _build_graph_from_story(story)
    health = graph_health(graph)
    return GraphHealthResponse(**health)


@router.get("/centrality/{entity_code}/{record_id}", response_model=CentralityResponse)
def get_centrality(
    entity_code: str,
    record_id: UUID,
    request: Request,
    depth: int = Query(default=3, ge=1, le=10),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> CentralityResponse:
    """Get centrality metrics for the graph"""
    story = build_story(
        db,
        tenant_id=tenant_id,
        role=request.state.role,
        entity_code=entity_code,
        record_id=record_id,
        depth=depth,
    )
    graph = _build_graph_from_story(story)
    return CentralityResponse(
        degree=degree_centrality(graph),
        betweenness=betweenness_centrality(graph),
        closeness=closeness_centrality(graph),
    )


@router.get("/cycles/{entity_code}/{record_id}", response_model=CyclesResponse)
def get_cycles(
    entity_code: str,
    record_id: UUID,
    request: Request,
    depth: int = Query(default=3, ge=1, le=10),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> CyclesResponse:
    """Detect cycles in the graph"""
    story = build_story(
        db,
        tenant_id=tenant_id,
        role=request.state.role,
        entity_code=entity_code,
        record_id=record_id,
        depth=depth,
    )
    graph = _build_graph_from_story(story)
    cycles = detect_cycles(graph)
    return CyclesResponse(
        has_cycles=len(cycles) > 0,
        cycles=cycles,
        count=len(cycles),
    )


# ---------------------------------------------------------------------------
# Business Graph V3 - Global Graph Endpoints
# ---------------------------------------------------------------------------

_TITLE_CANDIDATES = ("name", "title", "label", "code", "number")


def _build_global_graph(
    db: Session,
    tenant_id: UUID,
    max_nodes: int = 500,
) -> BusinessGraph:
    """Build a BusinessGraph from ALL records in the database for a tenant."""
    graph = BusinessGraph()

    entities = db.scalars(
        select(MetadataEntity).where(
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.published_at.is_not(None),
        ).order_by(MetadataEntity.version.desc())
    ).all()

    seen_entity_codes: set[str] = set()
    unique_entities: list[MetadataEntity] = []
    for e in entities:
        if e.code not in seen_entity_codes:
            seen_entity_codes.add(e.code)
            unique_entities.append(e)

    metadata_map: dict[str, MetadataEntity] = {e.code: e for e in unique_entities}
    node_count = 0

    for entity_code, metadata in metadata_map.items():
        if node_count >= max_nodes:
            break

        records = db.scalars(
            select(Record).where(
                Record.tenant_id == tenant_id,
                Record.entity_code == entity_code,
            ).limit(max_nodes - node_count)
        ).all()

        for record in records:
            if node_count >= max_nodes:
                break

            ref = f"{entity_code}:{record.id}"
            data = record.data or {}
            title = ""
            for code in _TITLE_CANDIDATES:
                value = data.get(code)
                if isinstance(value, str) and value:
                    title = value
                    break
            if not title:
                title = f"{entity_code} / {str(record.id)[-8:]}"

            graph.add_node(ref, {
                "ref": ref,
                "entity_code": entity_code,
                "record_id": str(record.id),
                "title": title,
                "data": data,
            })
            node_count += 1

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
                target_code = field.get("target_entity", "")
                target_ref = f"{target_code}:{target_id}"
                graph.add_edge(ref, target_ref, {
                    "field": field["code"],
                    "target_entity": target_code,
                })

    return graph


class GlobalGraphResponse(BaseModel):
    node_count: int
    edge_count: int
    entity_types: list[str]
    nodes: list[dict]
    edges: list[dict]
    health: dict


class GraphQueryRequest(BaseModel):
    start_ref: str = Field(min_length=1, max_length=200)
    end_ref: str = Field(min_length=1, max_length=200)
    max_depth: int = Field(default=10, ge=1, le=20)


class GraphQueryResponse(BaseModel):
    found: bool
    path: list[str] | None
    length: int | None
    nodes_in_path: list[dict]


class EntityGraphResponse(BaseModel):
    entity_code: str
    record_count: int
    nodes: list[dict]
    edges: list[dict]


@router.get("/global", response_model=GlobalGraphResponse)
def get_global_graph(
    request: Request,
    max_nodes: int = Query(default=200, ge=10, le=1000),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> GlobalGraphResponse:
    """Build the entire business graph for the tenant."""
    graph = _build_global_graph(db, tenant_id, max_nodes)
    health = graph_health(graph)
    entity_types = list({n.get("entity_code", "") for n in graph.nodes.values()})

    return GlobalGraphResponse(
        node_count=graph.node_count(),
        edge_count=graph.edge_count(),
        entity_types=sorted(entity_types),
        nodes=list(graph.nodes.values()),
        edges=[
            {"source": src, "target": e["target"], "field": e.get("field", ""), "target_entity": e.get("target_entity", "")}
            for src, edge_list in graph.edges.items()
            for e in edge_list
        ],
        health=health,
    )


@router.post("/query", response_model=GraphQueryResponse)
def query_graph_path(
    payload: GraphQueryRequest,
    request: Request,
    max_nodes: int = Query(default=200, ge=10, le=1000),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> GraphQueryResponse:
    """Find shortest path between any two records in the global graph."""
    graph = _build_global_graph(db, tenant_id, max_nodes)
    path = shortest_path(graph, payload.start_ref, payload.end_ref, payload.max_depth)

    nodes_in_path = []
    if path:
        for ref in path:
            node = graph.get_node(ref)
            if node:
                nodes_in_path.append(node)

    return GraphQueryResponse(
        found=path is not None,
        path=path,
        length=len(path) - 1 if path else None,
        nodes_in_path=nodes_in_path,
    )


@router.get("/entity/{entity_code}", response_model=EntityGraphResponse)
def get_entity_graph(
    entity_code: str,
    request: Request,
    max_nodes: int = Query(default=100, ge=10, le=500),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> EntityGraphResponse:
    """Get all records and relationships for a specific entity type."""
    graph = _build_global_graph(db, tenant_id, max_nodes)

    entity_nodes = [n for n in graph.nodes.values() if n.get("entity_code") == entity_code]
    entity_refs = {n["ref"] for n in entity_nodes}
    entity_edges = [
        {"source": src, "target": e["target"], "field": e.get("field", ""), "target_entity": e.get("target_entity", "")}
        for src, edge_list in graph.edges.items()
        for e in edge_list
        if src in entity_refs or e["target"] in entity_refs
    ]

    return EntityGraphResponse(
        entity_code=entity_code,
        record_count=len(entity_nodes),
        nodes=entity_nodes,
        edges=entity_edges,
    )


@router.get("/neighbors/{entity_code}/{record_id}")
def get_neighbors(
    entity_code: str,
    record_id: UUID,
    request: Request,
    direction: str = Query(default="both", pattern="^(outgoing|incoming|both)$"),
    max_depth: int = Query(default=1, ge=1, le=3),
    max_nodes: int = Query(default=200, ge=10, le=1000),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    """Get all neighbors of a record (outgoing, incoming, or both)."""
    graph = _build_global_graph(db, tenant_id, max_nodes)
    ref = f"{entity_code}:{record_id}"

    outgoing = []
    incoming = []

    if direction in ("outgoing", "both"):
        for edge in graph.edges.get(ref, []):
            node = graph.get_node(edge["target"])
            outgoing.append({"ref": edge["target"], "field": edge.get("field", ""), "node": node})

    if direction in ("incoming", "both"):
        for edge in graph.reverse_edges.get(ref, []):
            node = graph.get_node(edge["source"])
            incoming.append({"ref": edge["source"], "field": edge.get("field", ""), "node": node})

    return {
        "ref": ref,
        "outgoing": outgoing,
        "incoming": incoming,
        "total": len(outgoing) + len(incoming),
    }


@router.get("/stats")
def get_graph_stats(
    request: Request,
    max_nodes: int = Query(default=500, ge=10, le=1000),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    """Get overall graph statistics for the tenant."""
    graph = _build_global_graph(db, tenant_id, max_nodes)
    health = graph_health(graph)

    entity_distribution: dict[str, int] = {}
    for node in graph.nodes.values():
        ec = node.get("entity_code", "unknown")
        entity_distribution[ec] = entity_distribution.get(ec, 0) + 1

    top_connected = sorted(
        [(ref, len(edges)) for ref, edges in graph.edges.items()],
        key=lambda x: x[1],
        reverse=True,
    )[:10]

    return {
        "node_count": graph.node_count(),
        "edge_count": graph.edge_count(),
        "entity_distribution": entity_distribution,
        "entity_type_count": len(entity_distribution),
        "top_connected_nodes": [{"ref": ref, "edge_count": count} for ref, count in top_connected],
        "health": health,
    }


# ---------------------------------------------------------------------------
# Business Graph - Auto-Discovery
# ---------------------------------------------------------------------------

@router.post("/auto-discover")
def auto_discover_graph(
    request: Request,
    max_nodes: int = Query(default=500, ge=10, le=2000),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    """Auto-discover all entities, relationships, and build the graph."""
    graph = _build_global_graph(db, tenant_id, max_nodes)
    health = graph_health(graph)

    entity_types = {}
    for node in graph.nodes.values():
        ec = node.get("entity_code", "unknown")
        entity_types[ec] = entity_types.get(ec, 0) + 1

    discovered_relations = []
    for src, edge_list in graph.edges.items():
        for edge in edge_list:
            discovered_relations.append({
                "source": src,
                "target": edge["target"],
                "field": edge.get("field", ""),
                "source_entity": src.split(":")[0] if ":" in src else "",
                "target_entity": edge.get("target_entity", ""),
            })

    # Find orphaned nodes (no edges)
    nodes_with_edges = set()
    for src, edge_list in graph.edges.items():
        nodes_with_edges.add(src)
        for e in edge_list:
            nodes_with_edges.add(e["target"])
    orphaned = [ref for ref in graph.nodes if ref not in nodes_with_edges]

    # Find broken references (edges pointing to non-existent nodes)
    broken_refs = []
    for src, edge_list in graph.edges.items():
        for e in edge_list:
            if e["target"] not in graph.nodes:
                broken_refs.append({"source": src, "target": e["target"]})

    return {
        "status": "discovered",
        "entity_types": entity_types,
        "entity_type_count": len(entity_types),
        "total_nodes": graph.node_count(),
        "total_edges": graph.edge_count(),
        "discovered_relations": discovered_relations[:100],
        "relation_count": len(discovered_relations),
        "orphaned_nodes": orphaned[:50],
        "orphaned_count": len(orphaned),
        "broken_references": broken_refs[:50],
        "broken_ref_count": len(broken_refs),
        "health": health,
    }


# ---------------------------------------------------------------------------
# Business Graph Traversal — Entity Graph, Paths, Stories, Analytics
# ---------------------------------------------------------------------------


def _entity_graph(db: Session, tenant_id: UUID) -> EntityGraph:
    eg = EntityGraph(db, tenant_id)
    eg.build()
    return eg


@router.get("/map")
def get_graph_map(
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    """Full entity graph map — all entity types and their relationships."""
    eg = _entity_graph(db, tenant_id)
    analytics = GraphAnalytics(eg)
    return analytics.get_graph_map()


@router.get("/paths")
def find_entity_path(
    request: Request,
    from_entity: str = Query(..., min_length=1, max_length=100),
    to_entity: str = Query(..., min_length=1, max_length=100),
    max_depth: int = Query(default=5, ge=1, le=10),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    """Find shortest path between two entity types."""
    eg = _entity_graph(db, tenant_id)
    path = eg.find_path(from_entity, to_entity, max_depth=max_depth)
    return {
        "found": path is not None,
        "from": from_entity,
        "to": to_entity,
        "path": path,
        "length": len(path) - 1 if path else None,
    }


@router.get("/entity/{entity_code}/{record_id}/story")
def get_entity_story(
    entity_code: str,
    record_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    """Get the full business story for a record — all related data."""
    eg = _entity_graph(db, tenant_id)
    return eg.get_entity_story(entity_code, str(record_id))


@router.get("/entity/{entity_code}/{record_id}/related")
def get_related_records(
    entity_code: str,
    record_id: UUID,
    request: Request,
    depth: int = Query(default=1, ge=1, le=5),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    """Get all related records for a specific entity instance."""
    eg = _entity_graph(db, tenant_id)
    return eg.get_related_records(entity_code, str(record_id), depth=depth)


@router.get("/analytics/most-connected")
def get_most_connected(
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    """Which entities have the most relationships?"""
    eg = _entity_graph(db, tenant_id)
    analytics = GraphAnalytics(eg)
    return {"entities": analytics.get_most_connected_entities()}


@router.get("/analytics/orphans")
def get_orphan_entities(
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    """Which entities have no relationships?"""
    eg = _entity_graph(db, tenant_id)
    analytics = GraphAnalytics(eg)
    orphans = analytics.get_orphan_entities()
    return {"orphan_entities": orphans, "count": len(orphans)}


@router.get("/financial-flow")
def trace_financial_flow(
    request: Request,
    from_entity: str = Query(..., min_length=1, max_length=100),
    to_entity: str = Query(..., min_length=1, max_length=100),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    """Trace the financial flow between two entity types."""
    eg = _entity_graph(db, tenant_id)
    analytics = GraphAnalytics(eg)
    return analytics.get_financial_flow(from_entity, to_entity)
