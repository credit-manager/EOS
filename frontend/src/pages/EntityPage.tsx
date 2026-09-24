import { useState, useEffect } from 'react';
import { api } from '../api';
import { useI18n } from '../i18n';

interface Field { code: string; type: string; name: string; required: boolean; computed: boolean; }
interface EntityRecord { id: string; entity_code: string; data: Record<string, unknown>; version: number; workflow_instance_id?: string | null; }
interface EntityMeta { code: string; name?: string; description?: string; definition?: { fields?: Record<string, unknown>[] }; record_count?: number; }
interface RelatedEntity { entity_code: string; count: number; }

type Tab = 'overview' | 'data' | 'documents' | 'timeline' | 'ai';

export function EntityPage({ token, role, entityCode, onBack }: { token: string; role: string; entityCode: string; onBack: () => void }) {
  const { t } = useI18n();
  const [meta, setMeta] = useState<EntityMeta | null>(null);
  const [fields, setFields] = useState<Field[]>([]);
  const [records, setRecords] = useState<EntityRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>('overview');
  const [showCreate, setShowCreate] = useState(false);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [selectedRecord, setSelectedRecord] = useState<EntityRecord | null>(null);
  const [aiQuery, setAiQuery] = useState('');
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [relatedEntities] = useState<RelatedEntity[]>([]);

  useEffect(() => {
    Promise.all([
      api<EntityMeta>(`/metadata/entities/${entityCode}`, token),
      api<EntityRecord[]>(`/entities/${entityCode}/records`, token),
    ]).then(([m, recs]) => {
      setMeta(m);
      const raw = (m.definition?.fields ?? []) as Record<string, unknown>[];
      setFields(raw.map(f => ({ code: String(f.code ?? ''), type: String(f.type ?? 'text'), name: String(f.name ?? f.code ?? ''), required: Boolean(f.required), computed: Boolean(f.computed) })));
      setRecords(Array.isArray(recs) ? recs : []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [token, entityCode]);

  const handleCreate = async () => {
    setError(null);
    try {
      const data: Record<string, unknown> = {};
      for (const field of fields) {
        const v = formData[field.code];
        if (v === undefined || v === '') continue;
        if (field.type === 'integer') data[field.code] = parseInt(v, 10);
        else if (field.type === 'decimal') data[field.code] = Number(v);
        else if (field.type === 'boolean') data[field.code] = v === 'true';
        else data[field.code] = v;
      }
      await api(`/entities/${entityCode}/records`, token, { method: 'POST', body: JSON.stringify({ data }) });
      const recs = await api<EntityRecord[]>(`/entities/${entityCode}/records`, token);
      setRecords(Array.isArray(recs) ? recs : []);
      setShowCreate(false);
      setFormData({});
    } catch (e) { setError(e instanceof Error ? e.message : t.entityPage.createFailed); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t.entityPage.confirmDelete)) return;
    try {
      await api(`/entities/${entityCode}/records/${id}`, token, { method: 'DELETE' });
      setRecords(prev => prev.filter(r => r.id !== id));
      if (selectedRecord?.id === id) setSelectedRecord(null);
    } catch {}
  };

  const handleAskAboutEntity = async () => {
    if (!aiQuery.trim()) return;
    setAiResponse(null);
    try {
      const r = await fetch('/api/v1/ai/execute', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_code: 'data_analyst', input: { query: aiQuery, entity: entityCode, record_count: records.length } }),
      });
      if (r.ok) { const d = await r.json(); setAiResponse(d.output?.response || t.entityPage.analysisComplete); }
      else { setAiResponse(t.entityPage.analysisInitializing); }
    } catch { setAiResponse(t.entityPage.aiEngineConnecting); }
    setAiQuery('');
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>;

  const editableFields = fields.filter(f => !f.computed);
  const entityTotal = records.length;
  const fieldCount = fields.length;
  const dataCompleteness = fields.length > 0 ? Math.round((records.reduce((acc, rec) => acc + fields.filter(f => rec.data[f.code] != null && rec.data[f.code] !== '').length, 0) / (entityTotal * fieldCount)) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Entity Header */}
      <div className="flex items-center gap-4">
        <button onClick={onBack} className="text-gray-500 hover:text-gray-700 text-sm">&larr; {t.entityPage.back}</button>
        <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center text-white text-xl font-bold">
          {entityCode[0]?.toUpperCase()}
        </div>
        <div className="flex-1">
          <h2 className="text-2xl font-bold text-gray-900">{meta?.name || entityCode}</h2>
          <p className="text-gray-500 text-sm">{meta?.description || `${entityTotal} ${t.entityPage.recordsLabel} &middot; ${fieldCount} ${t.entityPage.fieldsLabel}`}</p>
        </div>
        {role !== 'viewer' && (
          <button onClick={() => setShowCreate(!showCreate)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            {showCreate ? t.entityPage.cancel : `+ ${t.entityPage.newRecord}`}
          </button>
        )}
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: t.entityPage.recordsLabel, value: entityTotal, icon: '📦', color: 'text-blue-600' },
          { label: t.entityPage.fieldsLabel, value: fieldCount, icon: '📋', color: 'text-purple-600' },
          { label: t.entityPage.dataQuality, value: `${dataCompleteness}%`, icon: '✅', color: 'text-green-600' },
          { label: t.entityPage.version, value: records[0]?.version || 1, icon: '🔄', color: 'text-orange-600' },
        ].map(s => (
          <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-4 text-center">
            <span className="text-xl">{s.icon}</span>
            <p className={`text-2xl font-bold mt-1 ${s.color}`}>{s.value}</p>
            <p className="text-xs text-gray-500">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
        {([
          ['overview', t.entityPage.tabOverview],
          ['data', `${t.entityPage.tabData} (${entityTotal})`],
          ['documents', t.entityPage.tabDocuments],
          ['timeline', t.entityPage.tabTimeline],
          ['ai', t.entityPage.tabAi],
        ] as const).map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)} className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${tab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
            {label}
          </button>
        ))}
      </div>

      {error && <div className="px-4 py-2 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}

      {/* Tab Content */}
      {tab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.entityPage.entityDefinition}</h3>
            <div className="space-y-2">
              <div className="flex justify-between py-2 border-b border-gray-100"><span className="text-sm text-gray-500">{t.entityPage.code}</span><span className="text-sm font-mono font-medium">{entityCode}</span></div>
              <div className="flex justify-between py-2 border-b border-gray-100"><span className="text-sm text-gray-500">{t.entityPage.totalRecords}</span><span className="text-sm font-medium">{entityTotal}</span></div>
              <div className="flex justify-between py-2 border-b border-gray-100"><span className="text-sm text-gray-500">{t.entityPage.editableFields}</span><span className="text-sm font-medium">{editableFields.length}</span></div>
              <div className="flex justify-between py-2 border-b border-gray-100"><span className="text-sm text-gray-500">{t.entityPage.computedFields}</span><span className="text-sm font-medium">{fields.length - editableFields.length}</span></div>
              <div className="flex justify-between py-2"><span className="text-sm text-gray-500">{t.entityPage.dataQuality}</span><span className={`text-sm font-medium ${dataCompleteness > 80 ? 'text-green-600' : dataCompleteness > 50 ? 'text-yellow-600' : 'text-red-600'}`}>{dataCompleteness}%</span></div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.entityPage.fieldsSchema}</h3>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {fields.map(f => (
                <div key={f.code} className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0">
                  <span className={`w-2 h-2 rounded-full ${f.computed ? 'bg-purple-400' : 'bg-blue-400'}`} />
                  <span className="text-sm font-medium text-gray-900 flex-1">{f.name || f.code}</span>
                  <span className="text-xs text-gray-400 font-mono">{f.type}</span>
                  {f.required && <span className="text-xs text-red-500">{t.entityPage.required}</span>}
                  {f.computed && <span className="text-xs text-purple-500">{t.entityPage.computed}</span>}
                </div>
              ))}
            </div>
          </div>
          {relatedEntities.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5 lg:col-span-2">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.entityPage.relatedEntities}</h3>
              <div className="grid grid-cols-3 gap-3">
                {relatedEntities.map(re => (
                  <div key={re.entity_code} className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-sm font-medium text-gray-900">{re.entity_code}</p>
                    <p className="text-xs text-gray-500">{re.count} records</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'data' && (
        <>
          {showCreate && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">{t.entityPage.newRecordTitle}</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {editableFields.map(f => (
                  <div key={f.code}>
                    <label className="block text-xs font-medium text-gray-600 mb-1">{f.name || f.code} {f.required && <span className="text-red-500">*</span>}</label>
                    <input type={f.type === 'integer' || f.type === 'decimal' ? 'number' : f.type === 'date' ? 'date' : 'text'} value={formData[f.code] ?? ''} onChange={e => setFormData({ ...formData, [f.code]: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" />
                  </div>
                ))}
              </div>
              <button onClick={handleCreate} className="mt-3 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">{t.entityPage.save}</button>
            </div>
          )}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    {fields.slice(0, 8).map(f => (
                      <th key={f.code} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{f.name || f.code}</th>
                    ))}
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">{t.entityPage.versionColumn}</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">{t.entityPage.actionsColumn}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {records.map(rec => (
                    <tr key={rec.id} className={`hover:bg-gray-50 cursor-pointer ${selectedRecord?.id === rec.id ? 'bg-blue-50' : ''}`} onClick={() => setSelectedRecord(selectedRecord?.id === rec.id ? null : rec)}>
                      {fields.slice(0, 8).map(f => (
                        <td key={f.code} className="px-4 py-3 text-gray-700 max-w-[200px] truncate">{String(rec.data[f.code] ?? '—')}</td>
                      ))}
                      <td className="px-4 py-3 text-gray-400">{rec.version}</td>
                      <td className="px-4 py-3 text-right">
                        {role !== 'viewer' && <button onClick={e => { e.stopPropagation(); handleDelete(rec.id); }} className="text-red-500 hover:text-red-700 text-xs">{t.entityPage.delete}</button>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {records.length === 0 && <div className="text-center py-8 text-gray-400 text-sm">{t.entityPage.noRecords}</div>}
          </div>
          {selectedRecord && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-gray-900">{t.entityPage.recordDetails}</h3>
                <button onClick={() => setSelectedRecord(null)} className="text-gray-400 hover:text-gray-600">&times;</button>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {fields.map(f => (
                  <div key={f.code} className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-500">{f.name || f.code}</p>
                    <p className="text-sm font-medium text-gray-900 mt-1">{String(selectedRecord.data[f.code] ?? '—')}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {tab === 'documents' && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <p className="text-4xl mb-3">📄</p>
          <p className="text-gray-500">{t.entityPage.documentIntelligence}</p>
          <p className="text-sm text-gray-400 mt-1">{t.entityPage.documentHint}</p>
          <button className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">{t.entityPage.uploadDocument}</button>
        </div>
      )}

      {tab === 'timeline' && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.entityPage.entityTimeline}</h3>
          <div className="space-y-3">
            {records.slice(0, 10).map((rec, i) => (
              <div key={rec.id} className="flex items-start gap-3">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 text-xs font-bold shrink-0">{i + 1}</div>
                <div className="flex-1 pb-3 border-b border-gray-100 last:border-0">
                  <p className="text-sm font-medium text-gray-900">{t.entityPage.recordCreated}</p>
                  <p className="text-xs text-gray-500">{t.entityPage.versionLabel} {rec.version} &middot; {rec.id.slice(0, 8)}</p>
                </div>
              </div>
            ))}
            {records.length === 0 && <p className="text-center text-gray-400 py-8">{t.entityPage.noTimelineData}</p>}
          </div>
        </div>
      )}

      {tab === 'ai' && (
        <div className="space-y-4">
          <div className="bg-gradient-to-r from-indigo-600 to-purple-700 rounded-2xl p-6 text-white">
            <h3 className="font-bold text-lg mb-2">{t.entityPage.aiInsightsFor} {entityCode}</h3>
            <p className="text-indigo-100 text-sm mb-4">{t.entityPage.aiInsightsSubtitle}</p>
            <div className="flex gap-3">
              <input type="text" value={aiQuery} onChange={e => setAiQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleAskAboutEntity()} placeholder={t.entityPage.aiAskPlaceholder} className="flex-1 px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-indigo-200 focus:outline-none" />
              <button onClick={handleAskAboutEntity} className="px-6 py-3 bg-white text-indigo-700 font-semibold rounded-xl hover:bg-indigo-50">{t.entityPage.ask}</button>
            </div>
          </div>
          {aiResponse && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-sm text-gray-700 leading-relaxed">{aiResponse}</p>
            </div>
          )}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[t.entityPage.showDuplicates, t.entityPage.dataQualityIssues, t.entityPage.trendsOverTime, t.entityPage.anomalies].map(q => (
              <button key={q} onClick={() => { setAiQuery(q); }} className="p-3 bg-white border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50 text-left">{q}</button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
