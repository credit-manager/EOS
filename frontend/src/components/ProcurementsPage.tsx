import { useState, useEffect } from 'react';
import { TranslationKeys } from '../i18n';

interface Procurement {
  id: string;
  project_id: string;
  requisition_number: string;
  title: string;
  description: string;
  priority: string;
  status: string;
  total_estimated: string;
  created_at: string;
}

type ProcurementTab = 'overview' | 'requests' | 'suppliers' | 'orders' | 'analysis' | 'ai';

export default function ProcurementsPage({ t, token }: { t: TranslationKeys; token: string }) {
  const [items, setItems] = useState<Procurement[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<ProcurementTab>('overview');
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<Procurement | null>(null);
  const [formData, setFormData] = useState({ requisition_number: '', title: '', description: '', priority: 'medium', status: 'draft' });
  const [aiQuery, setAiQuery] = useState('');
  const [aiResponse, setAiResponse] = useState<string | null>(null);

  useEffect(() => { fetchItems(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchItems = async () => {
    try {
      const r = await fetch('/api/v1/construction/procurements', { headers: { Authorization: `Bearer ${token}` } });
      if (r.ok) { const d = await r.json(); const rows = d.items || d; setItems((Array.isArray(rows) ? rows : []).map((p: Record<string, unknown>) => ({ id: String(p.id ?? ''), project_id: String(p.project_id ?? ''), requisition_number: String(p.requisition_number ?? ''), title: String(p.title ?? ''), description: String(p.description ?? ''), priority: String(p.priority ?? 'medium'), status: String(p.status ?? 'draft'), total_estimated: String(p.total_estimated ?? '0'), created_at: String(p.created_at ?? '') }))); }
    } catch { setError(t.common.error); } finally { setLoading(false); }
  };

  const handleCreate = async () => {
    setError(null);
    try {
      const r = await fetch('/api/v1/construction/procurements', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify(formData) });
      if (r.ok) { setShowCreate(false); setFormData({ requisition_number: '', title: '', description: '', priority: 'medium', status: 'draft' }); fetchItems(); }
      else { const d = await r.json(); setError(d.detail || t.common.error); }
    } catch { setError(t.common.error); }
  };

  const handleAskAI = async () => {
    if (!aiQuery.trim()) return;
    setAiResponse(null);
    try {
      const r = await fetch('/api/v1/ai/execute', { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ agent_code: 'procurement_agent', input: { query: aiQuery, procurements: items.length } }) });
      if (r.ok) { const d = await r.json(); setAiResponse(d.output?.response || 'Analysis complete.'); }
      else { setAiResponse('Analysis feature is being initialized.'); }
    } catch { setAiResponse('AI engine connecting...'); }
    setAiQuery('');
  };

  const priorityColor: Record<string, string> = { low: 'bg-gray-100 text-gray-800', medium: 'bg-blue-100 text-blue-800', high: 'bg-orange-100 text-orange-800', urgent: 'bg-red-100 text-red-800' };
  const statusColor: Record<string, string> = { draft: 'bg-gray-100 text-gray-800', pending_approval: 'bg-yellow-100 text-yellow-800', approved: 'bg-green-100 text-green-800', ordered: 'bg-blue-100 text-blue-800', received: 'bg-teal-100 text-teal-800', invoiced: 'bg-indigo-100 text-indigo-800', paid: 'bg-green-100 text-green-800', cancelled: 'bg-red-100 text-red-800' };

  const totalEstimated = items.reduce((a, c) => a + parseFloat(c.total_estimated || '0'), 0);
  const draftCount = items.filter(i => i.status === 'draft').length;
  const approvedCount = items.filter(i => i.status === 'approved').length;
  const orderedCount = items.filter(i => i.status === 'ordered').length;

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>;

  if (selectedItem) {
    const value = parseFloat(selectedItem.total_estimated || '0');
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <button onClick={() => setSelectedItem(null)} className="text-gray-500 hover:text-gray-700 text-sm">&larr; {t.procurementPage.tabRequests}</button>
          <div className="w-12 h-12 bg-gradient-to-br from-orange-500 to-amber-600 rounded-xl flex items-center justify-center text-white text-xl font-bold">{selectedItem.requisition_number[0]?.toUpperCase()}</div>
          <div className="flex-1"><h2 className="text-2xl font-bold text-gray-900">{selectedItem.title}</h2><p className="text-gray-500 text-sm">{selectedItem.requisition_number} &middot; {selectedItem.description || t.builderPage.noDescription}</p></div>
          <span className={`px-3 py-1 text-sm font-medium rounded-full ${statusColor[selectedItem.status] || 'bg-gray-100 text-gray-800'}`}>{selectedItem.status}</span>
        </div>
        <div className="grid grid-cols-4 gap-4">
          {[['Estimated', `$${value.toLocaleString()}`, '💰', 'text-orange-600'], [t.procurementPage.priority, selectedItem.priority, '🔥', 'text-red-600'], [t.procurementPage.title, selectedItem.status, '📊', 'text-green-600'], ['Created', selectedItem.created_at ? new Date(selectedItem.created_at).toLocaleDateString() : '—', '📅', 'text-purple-600']].map(([k, v, icon, c]) => (
            <div key={String(k)} className="bg-white rounded-xl border border-gray-200 p-4 text-center"><span className="text-xl">{icon}</span><p className={`text-lg font-bold mt-1 ${c}`}>{String(v)}</p><p className="text-xs text-gray-500">{String(k)}</p></div>
          ))}
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.procurementPage.details}</h3>
          <div className="space-y-2">
            {[['Number', selectedItem.requisition_number], ['Title', selectedItem.title], ['Description', selectedItem.description || '—'], [t.procurementPage.priority, selectedItem.priority], [t.procurementPage.status, selectedItem.status], ['Est. Value', `$${value.toLocaleString()}`]].map(([k, v]) => (
              <div key={String(k)} className="flex justify-between py-2 border-b border-gray-100"><span className="text-sm text-gray-500">{String(k)}</span><span className="text-sm font-medium">{String(v)}</span></div>
            ))}
          </div>
        </div>
        <div className="bg-gradient-to-r from-orange-600 to-amber-700 rounded-2xl p-6 text-white">
          <h3 className="font-bold text-lg mb-2">AI Procurement Advisor</h3>
          <div className="flex gap-3">
            <input type="text" value={aiQuery} onChange={e => setAiQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleAskAI()} placeholder={t.procurementPage.aiPlaceholder} className="flex-1 px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-orange-200 focus:outline-none" />
            <button onClick={handleAskAI} className="px-6 py-3 bg-white text-orange-700 font-semibold rounded-xl hover:bg-orange-50">{t.procurementPage.ask}</button>
          </div>
          {aiResponse && <div className="mt-3 p-3 bg-white/10 rounded-lg text-sm">{aiResponse}</div>}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t.procurement.title}</h1>
          <p className="text-gray-500 mt-1">{items.length} procurement requests &middot; ${totalEstimated.toLocaleString()} total estimated</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">{showCreate ? t.procurementPage.cancel : t.procurementPage.newRequest}</button>
      </div>

      {error && <div className="px-4 py-2 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}

      {showCreate && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-3">{t.procurementPage.newProcurementRequest}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.procurementPage.requisitionNumber}</label><input type="text" value={formData.requisition_number} onChange={e => setFormData({ ...formData, requisition_number: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
            <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.procurementPage.title}</label><input type="text" value={formData.title} onChange={e => setFormData({ ...formData, title: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
            <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.procurementPage.priority}</label><select value={formData.priority} onChange={e => setFormData({ ...formData, priority: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"><option value="low">{t.procurementPage.low}</option><option value="medium">{t.procurementPage.medium}</option><option value="high">{t.procurementPage.high}</option><option value="urgent">{t.procurementPage.urgent}</option></select></div>
          </div>
          <div className="flex gap-2 mt-3"><button onClick={handleCreate} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">{t.procurementPage.save}</button><button onClick={() => setShowCreate(false)} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">{t.procurementPage.cancel}</button></div>
        </div>
      )}

      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
        {([['overview', t.procurementPage.tabOverview], ['requests', t.procurementPage.tabRequests], ['suppliers', t.procurementPage.tabSuppliers], ['orders', t.procurementPage.tabOrders], ['analysis', t.procurementPage.tabAnalysis], ['ai', t.procurementPage.tabAi]] as const).map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)} className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${tab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>{label}</button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[[t.procurementPage.totalRequests, items.length, '📋', 'text-blue-600'], [t.procurementPage.draft, draftCount, '📝', 'text-gray-600'], [t.procurementPage.approved, approvedCount, '✅', 'text-green-600'], [t.procurementPage.ordered, orderedCount, '🛒', 'text-orange-600']].map(([k, v, icon, c]) => (
              <div key={String(k)} className="bg-white rounded-xl border border-gray-200 p-4 text-center"><span className="text-xl">{icon}</span><p className={`text-2xl font-bold mt-1 ${c}`}>{v as number}</p><p className="text-xs text-gray-500">{String(k)}</p></div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.procurementPage.priorityDistribution}</h3>
              <div className="space-y-2">
                {[['urgent', items.filter(i => i.priority === 'urgent').length], ['high', items.filter(i => i.priority === 'high').length], ['medium', items.filter(i => i.priority === 'medium').length], ['low', items.filter(i => i.priority === 'low').length]].map(([p, count]) => (
                  <div key={String(p)} className="flex items-center gap-3">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${priorityColor[String(p)]}`}>{String(p)}</span>
                    <div className="flex-1 h-2 bg-gray-100 rounded-full"><div className="h-2 bg-orange-500 rounded-full transition-all" style={{ width: `${items.length ? (count as number) / items.length * 100 : 0}%` }} /></div>
                    <span className="text-sm font-medium text-gray-600 w-8 text-right">{count as number}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.procurementPage.recentRequests}</h3>
              <div className="space-y-2">
                {items.slice(0, 5).map(i => (
                  <div key={i.id} onClick={() => setSelectedItem(i)} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100">
                    <div><p className="text-sm font-medium text-gray-900">{i.title}</p><p className="text-xs text-gray-500">{i.requisition_number}</p></div>
                    <div className="flex items-center gap-2"><span className={`px-2 py-1 text-xs font-medium rounded-full ${priorityColor[i.priority] || 'bg-gray-100 text-gray-800'}`}>{i.priority}</span><span className={`px-2 py-1 text-xs font-medium rounded-full ${statusColor[i.status] || 'bg-gray-100 text-gray-800'}`}>{i.status}</span></div>
                  </div>
                ))}
                {items.length === 0 && <p className="text-sm text-gray-400 text-center py-4">{t.procurementPage.noProcurementRequests}</p>}
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === 'requests' && (
        <div className="bg-white rounded-xl border border-gray-200">
          <table className="w-full">
            <thead><tr className="border-b border-gray-200"><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.procurementPage.requisition}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.procurementPage.title}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.procurementPage.priority}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.procurementPage.estValue}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.procurementPage.status}</th></tr></thead>
            <tbody>
              {items.map(i => (
                <tr key={i.id} onClick={() => setSelectedItem(i)} className="border-b border-gray-100 last:border-0 hover:bg-gray-50 cursor-pointer">
                  <td className="px-4 py-3 text-sm font-mono text-gray-900">{i.requisition_number}</td>
                  <td className="px-4 py-3 text-sm text-gray-900">{i.title}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-1 text-xs font-medium rounded-full ${priorityColor[i.priority] || 'bg-gray-100 text-gray-800'}`}>{i.priority}</span></td>
                  <td className="px-4 py-3 text-sm font-mono text-gray-900">{`$${parseFloat(i.total_estimated || '0').toLocaleString()}`}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-1 text-xs font-medium rounded-full ${statusColor[i.status] || 'bg-gray-100 text-gray-800'}`}>{i.status}</span></td>
                </tr>
              ))}
              {items.length === 0 && <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">{t.procurementPage.noRequests}</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'suppliers' && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <p className="text-4xl mb-3">🏭</p>
          <p className="text-gray-500 font-medium">{t.procurementPage.supplierManagement}</p>
          <p className="text-sm text-gray-400 mt-1">{t.procurementPage.supplierManagementDesc}</p>
        </div>
      )}

      {tab === 'orders' && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <p className="text-4xl mb-3">🛒</p>
          <p className="text-gray-500 font-medium">{t.procurementPage.purchaseOrders}</p>
          <p className="text-sm text-gray-400 mt-1">{t.procurementPage.purchaseOrdersDesc}</p>
        </div>
      )}

      {tab === 'analysis' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              [t.procurementPage.totalValue, `$${totalEstimated.toLocaleString()}`, '💰', 'text-orange-600'],
              [t.procurementPage.avgPerRequest, items.length ? `$${(totalEstimated / items.length).toFixed(0)}` : '$0', '📊', 'text-blue-600'],
              [t.procurementPage.pending, items.filter(i => i.status === 'draft' || i.status === 'pending_approval').length, '⏳', 'text-yellow-600'],
            ].map(([k, v, icon, c]) => (
              <div key={String(k)} className="bg-white rounded-xl border border-gray-200 p-5 text-center"><span className="text-2xl">{icon}</span><p className={`text-2xl font-bold mt-2 ${c}`}>{String(v)}</p><p className="text-sm text-gray-500 mt-1">{String(k)}</p></div>
            ))}
          </div>
        </div>
      )}

      {tab === 'ai' && (
        <div className="space-y-4">
          <div className="bg-gradient-to-r from-orange-600 to-amber-700 rounded-2xl p-6 text-white">
          <h3 className="font-bold text-lg mb-2">{t.procurementPage.aiProcurementAdvisor}</h3>
            <p className="text-orange-100 text-sm mb-4">{t.procurementPage.aiProcurementDesc}</p>
            <div className="flex gap-3">
              <input type="text" value={aiQuery} onChange={e => setAiQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleAskAI()} placeholder={t.procurementPage.aiPlaceholder} className="flex-1 px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-orange-200 focus:outline-none" />
              <button onClick={handleAskAI} className="px-6 py-3 bg-white text-orange-700 font-semibold rounded-xl hover:bg-orange-50">{t.procurementPage.ask}</button>
            </div>
          </div>
          {aiResponse && <div className="bg-white rounded-xl border border-gray-200 p-5"><p className="text-sm text-gray-700 leading-relaxed">{aiResponse}</p></div>}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {['Cost optimization', 'Supplier comparison', 'Lead time analysis', 'Budget forecast'].map(q => (
              <button key={q} onClick={() => setAiQuery(q)} className="p-3 bg-white border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50 text-left">{q}</button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
