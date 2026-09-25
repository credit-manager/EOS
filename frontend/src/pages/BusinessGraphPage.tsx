import { useState, useEffect, useCallback } from 'react';
import { useI18n } from '../i18n';

interface Entity { id: string; code: string; name: string; version: number; field_count: number; permissions: string[]; }
interface EntityRecord { id: string; entity_code: string; data: Record<string, unknown>; version: number; workflow_instance_id: string; }
interface GraphNode { ref: string; entity_code: string; record_id: string; title: string; data: Record<string, unknown>; }
interface GraphEdge { source: string; target: string; field: string; target_entity: string; }
interface GraphStory { root: GraphNode; nodes: GraphNode[]; edges: GraphEdge[]; depth: number; }

const PALETTE = ['#3b82f6', '#22c55e', '#a855f7', '#f59e0b', '#f43f5e', '#06b6d4', '#8b5cf6', '#ec4899'] as const;
const ENTITY_COLORS = new Map<string, string>();

function getColor(entity: string): string {
  if (!ENTITY_COLORS.has(entity)) ENTITY_COLORS.set(entity, PALETTE[ENTITY_COLORS.size % PALETTE.length]);
  return ENTITY_COLORS.get(entity) ?? PALETTE[0];
}

function truncate(str: string, max: number): string { return str.length > max ? str.slice(0, max) + '…' : str; }

function computeLayout(story: GraphStory, cx: number, cy: number) {
  const dist = new Map<string, number>();
  dist.set(story.root.ref, 0);
  const adj = new Map<string, string[]>();
  for (const e of story.edges) {
    if (!adj.has(e.source)) adj.set(e.source, []);
    adj.get(e.source)!.push(e.target);
    if (!adj.has(e.target)) adj.set(e.target, []);
    adj.get(e.target)!.push(e.source);
  }
  const queue = [story.root.ref];
  while (queue.length > 0) {
    const cur = queue.shift()!;
    const d = dist.get(cur)!;
    for (const nb of adj.get(cur) ?? []) {
      if (!dist.has(nb)) { dist.set(nb, d + 1); queue.push(nb); }
    }
  }
  const posMap = new Map<string, { x: number; y: number }>();
  posMap.set(story.root.ref, { x: cx, y: cy });
  const allNodes = [story.root, ...story.nodes];
  const groups = new Map<number, GraphNode[]>();
  for (const node of allNodes) {
    const d = dist.get(node.ref) ?? 1;
    if (!groups.has(d)) groups.set(d, []);
    groups.get(d)!.push(node);
  }
  groups.forEach((group, d) => {
    if (d === 0) return;
    const radius = 140 * d;
    group.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / group.length - Math.PI / 2;
      posMap.set(node.ref, { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) });
    });
  });
  return { posMap, dist };
}

export function BusinessGraphPage({ token }: { token: string }) {
  const { t } = useI18n();
  const [entities, setEntities] = useState<Entity[]>([]);
  const [selectedEntity, setSelectedEntity] = useState('');
  const [entityRecords, setEntityRecords] = useState<EntityRecord[]>([]);
  const [selectedRecordId, setSelectedRecordId] = useState('');
  const [depth, setDepth] = useState(2);
  const [graph, setGraph] = useState<GraphStory | null>(null);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [loadingEntities, setLoadingEntities] = useState(true);
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [selectedNodeData, setSelectedNodeData] = useState<GraphNode | null>(null);

  useEffect(() => {
    setLoadingEntities(true);
    fetch('/api/v1/metadata/entities', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : [])
      .then(data => { const arr = Array.isArray(data) ? data : []; setEntities(arr); if (arr.length > 0) setSelectedEntity(arr[0].code); })
      .catch(() => setEntities([]))
      .finally(() => setLoadingEntities(false));
  }, [token]);

  useEffect(() => {
    if (!selectedEntity) { setEntityRecords([]); setSelectedRecordId(''); return; }
    setLoadingRecords(true); setEntityRecords([]); setSelectedRecordId(''); setGraph(null);
    fetch(`/api/v1/entities/${selectedEntity}/records?limit=200`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : [])
      .then(data => setEntityRecords(Array.isArray(data) ? data : []))
      .catch(() => setEntityRecords([]))
      .finally(() => setLoadingRecords(false));
  }, [selectedEntity, token]);

  const fetchGraph = useCallback(() => {
    if (!selectedEntity || !selectedRecordId) return;
    setLoadingGraph(true); setError(null);
    fetch(`/api/v1/graph/${selectedEntity}/${selectedRecordId}?depth=${depth}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => { if (!r.ok) throw new Error(`Graph fetch failed: ${r.status}`); return r.json(); })
      .then(data => { setGraph(data as GraphStory); setSelectedNodeData(null); })
      .catch(err => { setError(err instanceof Error ? err.message : 'Unknown error'); setGraph(null); })
      .finally(() => setLoadingGraph(false));
  }, [selectedEntity, selectedRecordId, depth, token]);

  useEffect(() => { fetchGraph(); }, [fetchGraph]);

  const svgW = 960, svgH = 640, cx = svgW / 2, cy = svgH / 2;

  const entityColorMap = new Map<string, string>();
  if (graph) {
    entityColorMap.set(graph.root.entity_code, getColor(graph.root.entity_code));
    graph.nodes.forEach(n => getColor(n.entity_code));
  }

  const layout = graph ? computeLayout(graph, cx, cy) : null;
  const getPos = (ref: string) => layout?.posMap.get(ref) ?? { x: 0, y: 0 };

  function recordLabel(rec: EntityRecord): string {
    const v = Object.values(rec.data)[0];
    return typeof v === 'string' && v.length > 0 ? truncate(v, 40) : rec.id.slice(0, 8);
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">{t.businessGraph.title}</h2>
        <p className="text-gray-500 mt-1">{t.businessGraph.subtitle}</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{t.businessGraph.entityType}</label>
            <select value={selectedEntity} onChange={e => setSelectedEntity(e.target.value)} disabled={loadingEntities}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 min-w-[180px]">
              {entities.map(ent => <option key={ent.id} value={ent.code}>{ent.name || ent.code}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{t.businessGraph.record}</label>
            <select value={selectedRecordId} onChange={e => setSelectedRecordId(e.target.value)} disabled={loadingRecords || entityRecords.length === 0}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 min-w-[220px]">
              {entityRecords.length === 0 && <option value="">{loadingRecords ? t.businessGraph.loading : t.businessGraph.noRecords}</option>}
              {entityRecords.map(rec => <option key={rec.id} value={rec.id}>{recordLabel(rec)}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{t.businessGraph.depth}: {depth}</label>
            <input type="range" min={1} max={3} value={depth} onChange={e => setDepth(Number(e.target.value))} className="w-40 accent-blue-600" />
          </div>
          <button onClick={fetchGraph} disabled={loadingGraph || !selectedRecordId}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {loadingGraph ? t.businessGraph.loading : t.businessGraph.refreshGraph}
          </button>
        </div>
      </div>

      {graph && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4 text-center"><p className="text-2xl font-bold text-blue-600">{graph.nodes.length + 1}</p><p className="text-xs text-gray-500 mt-0.5">{t.businessGraph.nodes}</p></div>
          <div className="bg-white rounded-xl border border-gray-200 p-4 text-center"><p className="text-2xl font-bold text-green-600">{graph.edges.length}</p><p className="text-xs text-gray-500 mt-0.5">{t.businessGraph.edges}</p></div>
          <div className="bg-white rounded-xl border border-gray-200 p-4 text-center"><p className="text-2xl font-bold text-purple-600">{graph.depth}</p><p className="text-xs text-gray-500 mt-0.5">{t.businessGraph.depth}</p></div>
          <div className="bg-white rounded-xl border border-gray-200 p-4 text-center"><p className="text-2xl font-bold text-amber-600">{new Set(graph.edges.map(e => e.target_entity)).size}</p><p className="text-xs text-gray-500 mt-0.5">{t.businessGraph.entityTypes}</p></div>
        </div>
      )}

      {graph && (
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-900 mb-2">{t.businessGraph.entryNode}</h3>
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
            <span className="text-gray-500">{t.businessGraph.entity}:</span><span className="text-gray-900 font-medium">{graph.root.entity_code}</span>
            <span className="text-gray-500">{t.businessGraph.titleLabel}:</span><span className="text-gray-900">{graph.root.title}</span>
            <span className="text-gray-500">{t.businessGraph.recordId}:</span><span className="text-gray-900 font-mono text-xs">{graph.root.record_id.slice(0, 12)}</span>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden relative">
        {loadingGraph && !graph ? (
          <div className="flex items-center justify-center h-[640px]"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>
        ) : error ? (
          <div className="flex items-center justify-center h-[400px] text-red-500 text-sm">{error}</div>
        ) : graph ? (
          <svg viewBox={`0 0 ${svgW} ${svgH}`} className="w-full h-auto" style={{ minHeight: 400 }}>
            <defs>
              <marker id="arrow" viewBox="0 0 10 7" refX="10" refY="3.5" markerWidth="8" markerHeight="6" orient="auto-start-reverse">
                <polygon points="0 0, 10 3.5, 0 7" fill="#9ca3af" />
              </marker>
              <filter id="glow"><feGaussianBlur stdDeviation="3" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
            </defs>
            {graph.edges.map((edge, i) => {
              const from = getPos(edge.source), to = getPos(edge.target);
              if (from.x === 0 && from.y === 0) return null;
              if (to.x === 0 && to.y === 0) return null;
              const isHovered = hoveredNode === edge.source || hoveredNode === edge.target;
              return <line key={`e-${i}`} x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke={isHovered ? '#3b82f6' : '#d1d5db'} strokeWidth={isHovered ? 2.5 : 1.5} markerEnd="url(#arrow)" />;
            })}
            {graph.edges.map((edge, i) => {
              const from = getPos(edge.source), to = getPos(edge.target);
              if (from.x === 0 || to.x === 0) return null;
              return <text key={`el-${i}`} x={(from.x + to.x) / 2} y={(from.y + to.y) / 2 - 4} textAnchor="middle" className="fill-gray-400 pointer-events-none" style={{ fontSize: 8 }}>{edge.field}</text>;
            })}
            {[graph.root, ...graph.nodes].map((node) => {
              const pos = getPos(node.ref);
              const isRoot = node.ref === graph.root.ref;
              const isHovered = hoveredNode === node.ref;
              const isSelected = selectedNodeData?.ref === node.ref;
              const fillColor = getColor(node.entity_code);
              const r = isRoot ? 38 : isHovered ? 28 : 24;
              return (
                <g key={node.ref} onMouseEnter={() => setHoveredNode(node.ref)} onMouseLeave={() => setHoveredNode(null)} onClick={() => setSelectedNodeData(selectedNodeData?.ref === node.ref ? null : node)} className="cursor-pointer">
                  <circle cx={pos.x} cy={pos.y} r={r + 8} fill={fillColor} opacity={isHovered || isSelected ? 0.2 : 0.1} />
                  <circle cx={pos.x} cy={pos.y} r={r} fill="white" stroke={isSelected ? fillColor : isHovered ? fillColor : '#e5e7eb'} strokeWidth={isSelected ? 3 : isHovered ? 2.5 : 2} filter={isHovered ? 'url(#glow)' : undefined} />
                  <circle cx={pos.x} cy={pos.y} r={r * 0.45} fill={fillColor} opacity={0.85} />
                  <text x={pos.x} y={pos.y + 2} textAnchor="middle" className="fill-white" style={{ fontSize: isRoot ? 11 : 9, fontWeight: 700 }}>{node.entity_code.slice(0, 2).toUpperCase()}</text>
                  <text x={pos.x} y={pos.y + r + 14} textAnchor="middle" className="fill-gray-700" style={{ fontSize: 10, fontWeight: 600 }}>{truncate(node.title, 24)}</text>
                  <text x={pos.x} y={pos.y + r + 24} textAnchor="middle" className="fill-gray-400" style={{ fontSize: 8 }}>{node.entity_code}</text>
                </g>
              );
            })}
          </svg>
        ) : (
          <div className="flex items-center justify-center h-[400px] text-gray-400 text-sm">{t.businessGraph.selectToVisualize}</div>
        )}
      </div>

      {selectedNodeData && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-900">{t.businessGraph.nodeDetails}</h3>
            <button onClick={() => setSelectedNodeData(null)} className="text-gray-400 hover:text-gray-600">&times;</button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-3 bg-gray-50 rounded-lg"><p className="text-xs text-gray-500">{t.businessGraph.entity}</p><p className="text-sm font-medium">{selectedNodeData.entity_code}</p></div>
            <div className="p-3 bg-gray-50 rounded-lg"><p className="text-xs text-gray-500">{t.businessGraph.titleLabel}</p><p className="text-sm font-medium">{selectedNodeData.title}</p></div>
            <div className="p-3 bg-gray-50 rounded-lg"><p className="text-xs text-gray-500">{t.businessGraph.recordId}</p><p className="text-sm font-mono text-xs">{selectedNodeData.record_id.slice(0, 12)}</p></div>
            <div className="p-3 bg-gray-50 rounded-lg"><p className="text-xs text-gray-500">{t.businessGraph.connections}</p><p className="text-sm font-medium">{graph?.edges.filter(e => e.source === selectedNodeData.ref || e.target === selectedNodeData.ref).length || 0}</p></div>
          </div>
          {selectedNodeData.data && Object.keys(selectedNodeData.data).length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <p className="text-xs font-medium text-gray-500 mb-2">{t.businessGraph.data}</p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {Object.entries(selectedNodeData.data).slice(0, 9).map(([k, v]) => (
                  <div key={k} className="text-xs"><span className="text-gray-500">{k}:</span> <span className="font-medium">{String(v ?? '—')}</span></div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {entityColorMap.size > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.businessGraph.entityLegend}</h3>
          <div className="flex flex-wrap gap-3">
            {Array.from(entityColorMap.entries()).map(([entity, color]) => (
              <div key={entity} className="flex items-center gap-2"><span className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} /><span className="text-sm text-gray-700">{entity}</span></div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
