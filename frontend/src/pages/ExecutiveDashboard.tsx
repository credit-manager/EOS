import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api';
import { useI18n } from '../i18n';

interface EntityCounter { entity_code: string; count: number; }
interface PendingApproval { id: string; workflow_instance_id: string; action: string; from_state: string; to_state: string; status: string; requested_by?: string; }
interface WorkflowAttention { instance_id: string; workflow_code: string; current_state: string; status: string; }
interface HomeData {
  entity_counts: EntityCounter[];
  approvals_pending: PendingApproval[];
  workflows_needing_action: WorkflowAttention[];
  recent_events: { event_type?: string; entity_type?: string; occurred_at?: string; created_at?: string; }[];
  recent_rule_firings: { rule_name?: string; id?: string; executed_at?: string; fired_at?: string; event_type?: string; }[];
  report_count: number;
}
interface DocStats { total: number; processed: number; failed: number; processing: number; by_category: Record<string, number>; }
interface AIResponse { response: string; sources?: string[]; actions?: string[]; intent?: string; data?: Record<string, unknown>; }
interface Project { id: string; code: string; name: string; status: string; budget: string; client_name: string; }
interface Risk { title: string; level: string; detail: string; action: string; }
interface Invoice { id: string; invoice_number: string; customer_id: string; status: string; issue_date: string; due_date: string; currency: string; total_amount: number; paid_amount: number; balance_due: number; }
interface Bill { id: string; bill_number: string; supplier_id: string; status: string; issue_date: string; due_date: string; currency: string; total_amount: number; paid_amount: number; balance_due: number; }
interface AgingData { as_of: string; buckets: Record<string, number>; total_outstanding: number; }

type Tab = 'overview' | 'attention' | 'financial' | 'activity' | 'risks';

export function ExecutiveDashboard({ token }: { token: string }) {
  const { t } = useI18n();
  const [home, setHome] = useState<HomeData | null>(null);
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [docStats, setDocStats] = useState<DocStats | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [risks, setRisks] = useState<Risk[]>([]);
  const [loading, setLoading] = useState(true);
  const [aiQuery, setAiQuery] = useState('');
  const [aiResponse, setAiResponse] = useState<AIResponse | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<{ type: string; items: Array<{ id: string; name: string; code?: string; status?: string }> }[]>([]);
  const [showSearch, setShowSearch] = useState(false);
  const aiInputRef = useRef<HTMLInputElement>(null);

  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [bills, setBills] = useState<Bill[]>([]);
  const [arAging, setArAging] = useState<AgingData | null>(null);
  const [apAging, setApAging] = useState<AgingData | null>(null);

  const fetchData = useCallback(() => {
    setLoading(true);
    Promise.all([
      api<HomeData>('/analytics/home', token),
      api<PendingApproval[]>('/workflows/approvals?status=pending', token).catch(() => []),
      api<DocStats>('/documents/stats', token).catch(() => null),
      api<{ items: Project[] }>('/construction/projects', token).catch(() => ({ items: [] })),
      api<Invoice[]>('/financial/invoices', token).catch(() => []),
      api<Bill[]>('/financial/bills', token).catch(() => []),
      api<AgingData>('/financial/statements/ar-aging', token).catch(() => null),
      api<AgingData>('/financial/statements/ap-aging', token).catch(() => null),
    ]).then(([homeData, approvalData, ds, projData, invData, billData, arData, apData]) => {
      setHome(homeData);
      setApprovals(Array.isArray(approvalData) ? approvalData : []);
      setDocStats(ds);
      setProjects(Array.isArray(projData?.items) ? projData.items : Array.isArray(projData) ? projData : []);
      setInvoices(Array.isArray(invData) ? invData : []);
      setBills(Array.isArray(billData) ? billData : []);
      setArAging(arData);
      setApAging(apData);

      const newRisks: Risk[] = [];
      if (projData) {
        const projs = Array.isArray(projData?.items) ? projData.items : Array.isArray(projData) ? projData : [];
        projs.forEach((p: Project) => {
          const budget = parseFloat(p.budget || '0');
          if (budget > 1000000) newRisks.push({ title: `${p.name} - High Budget`, level: 'high', detail: `Budget: $${(budget / 1000000).toFixed(1)}M`, action: 'Review financial health' });
        });
      }
      if (approvalData && Array.isArray(approvalData) && approvalData.length > 5) {
        newRisks.push({ title: 'Approval Backlog', level: 'medium', detail: `${approvalData.length} items waiting`, action: 'Process approvals' });
      }
      const overdueInvoices = (Array.isArray(invData) ? invData : []).filter(i => i.status === 'overdue' || (i.status === 'sent' && new Date(i.due_date) < new Date()));
      if (overdueInvoices.length > 0) {
        newRisks.push({ title: 'Overdue Invoices', level: 'high', detail: `${overdueInvoices.length} invoices overdue`, action: 'Follow up with customers' });
      }
      const overdueBills = (Array.isArray(billData) ? billData : []).filter(b => b.status === 'overdue' || (b.status === 'received' && new Date(b.due_date) < new Date()));
      if (overdueBills.length > 0) {
        newRisks.push({ title: 'Overdue Bills', level: 'medium', detail: `${overdueBills.length} bills overdue`, action: 'Process payments' });
      }
      setRisks(newRisks);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    if (!searchQuery.trim()) { setSearchResults([]); setShowSearch(false); return; }
    const timer = setTimeout(() => {
      api<{ items: Project[] }>('/construction/projects', token).then(d => {
        const items = (d?.items || []).filter((p: Project) =>
          p.name?.toLowerCase().includes(searchQuery.toLowerCase()) || p.code?.toLowerCase().includes(searchQuery.toLowerCase())
        ).slice(0, 5);
        if (items.length > 0) setSearchResults([{ type: 'Projects', items }]);
      }).catch(() => {});
      setShowSearch(true);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, token]);

  const handleAskEOS = async () => {
    if (!aiQuery.trim() || aiLoading) return;
    setAiLoading(true);
    setAiResponse(null);
    try {
      const r = await api<{ answer: string; intent: string; sources: Array<{ entity: string; id: string; title: string }>; suggestions: string[]; confidence: number }>('/ai/ask', token, {
        method: 'POST',
        body: JSON.stringify({ query: aiQuery }),
      });
      setAiResponse({
        response: r?.answer || 'Analysis complete.',
        sources: (r?.sources || []).map((s: { entity: string; id: string; title: string }) => s.title),
        actions: [],
        intent: r?.intent,
      });
    } catch {
      setAiResponse({ response: 'I can help with projects, finances, procurement, approvals, and supplier analysis. Try asking about budget overruns or overdue invoices.', sources: [], actions: [] });
    }
    setAiLoading(false);
    setAiQuery('');
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>;

  const entityTotal = home ? home.entity_counts.reduce((a, b) => a + b.count, 0) : 0;
  const activeWorkflows = home ? home.workflows_needing_action.length : 0;
  const pendingApprovals = approvals.length;
  const totalAR = invoices.reduce((sum, i) => sum + i.balance_due, 0);
  const totalAP = bills.reduce((sum, b) => sum + b.balance_due, 0);
  const overdueInvoices = invoices.filter(i => i.status === 'overdue' || (i.status === 'sent' && new Date(i.due_date) < new Date()));
  const overdueBills = bills.filter(b => b.status === 'overdue' || (b.status === 'received' && new Date(b.due_date) < new Date()));
  const fmt = (n: number) => n.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  return (
    <div className="space-y-6">
      <div className="relative">
        <div className="flex items-center gap-3 bg-white rounded-xl border border-gray-200 px-4 py-3 shadow-sm">
          <span className="text-gray-400">🔍</span>
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onFocus={() => searchQuery && setShowSearch(true)}
            placeholder={t.executiveDashboard.searchPlaceholder}
            className="flex-1 text-sm focus:outline-none"
          />
          <button onClick={() => { setSearchQuery(''); setShowSearch(false); }} className="text-gray-400 hover:text-gray-600">&times;</button>
        </div>
        {showSearch && searchResults.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-2 bg-white rounded-xl border border-gray-200 shadow-lg z-50 max-h-64 overflow-y-auto">
            {searchResults.map(group => (
              <div key={group.type}>
                <p className="px-4 py-2 text-xs font-semibold text-gray-400 uppercase bg-gray-50">{group.type}</p>
                {group.items.map(item => (
                  <button key={item.id} className="w-full text-left px-4 py-2 hover:bg-gray-50 flex items-center gap-3" onClick={() => setShowSearch(false)}>
                    <span className="text-sm font-medium text-gray-900">{item.name}</span>
                    {item.code && <span className="text-xs text-gray-400 font-mono">{item.code}</span>}
                    {item.status && <span className="text-xs text-gray-500">{item.status}</span>}
                  </button>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{t.executiveDashboard.workspace}</h2>
          <p className="text-gray-500 mt-1">{t.executiveDashboard.whatNeedsAttention}</p>
        </div>
        <div className="text-right text-sm text-gray-400">
          {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </div>
      </div>

      <div className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-700 rounded-2xl p-6 text-white shadow-lg">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center text-xl">🤖</div>
          <div>
            <h3 className="font-bold text-lg">{t.executiveDashboard.askEos}</h3>
            <p className="text-blue-100 text-sm">{t.executiveDashboard.askEosSubtitle}</p>
          </div>
        </div>
        <div className="flex gap-3">
          <input
            ref={aiInputRef}
            type="text"
            value={aiQuery}
            onChange={e => setAiQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAskEOS()}
            placeholder={t.executiveDashboard.askEosPlaceholder}
            className="flex-1 px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-blue-200 focus:outline-none focus:ring-2 focus:ring-white/50"
          />
          <button onClick={handleAskEOS} disabled={aiLoading || !aiQuery.trim()} className="px-6 py-3 bg-white text-blue-700 font-semibold rounded-xl hover:bg-blue-50 transition-colors disabled:opacity-50">
            {aiLoading ? t.executiveDashboard.analyzing : t.executiveDashboard.askEos}
          </button>
        </div>
        {aiResponse && (
          <div className="mt-4 bg-white/10 rounded-xl p-4 border border-white/20">
            {aiResponse.intent && <p className="text-xs text-blue-200 mb-1">Intent: {aiResponse.intent}</p>}
            <p className="text-sm leading-relaxed">{aiResponse.response}</p>
            {aiResponse.sources && aiResponse.sources.length > 0 && (
              <div className="mt-2 flex gap-2 flex-wrap">
                {aiResponse.sources.map((s, i) => (
                  <span key={i} className="px-2 py-0.5 bg-white/10 rounded text-xs">{s}</span>
                ))}
              </div>
            )}
          </div>
        )}
        <div className="mt-3 flex gap-2 flex-wrap">
          {[t.executiveDashboard.suggestApproval, t.executiveDashboard.suggestOverdue, t.executiveDashboard.suggestArAging, t.executiveDashboard.suggestProjectHealth, t.executiveDashboard.suggestTopSuppliers, t.executiveDashboard.suggestBudgetReport].map(q => (
            <button key={q} onClick={() => { setAiQuery(q); aiInputRef.current?.focus(); }} className="px-3 py-1 bg-white/10 rounded-lg text-xs text-blue-100 hover:bg-white/20 transition-colors">{q}</button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        {[
          { label: t.executiveDashboard.statRecords, value: entityTotal, color: 'bg-blue-50 text-blue-600 border-blue-200', icon: '📦' },
          { label: t.executiveDashboard.statApprovals, value: pendingApprovals, color: pendingApprovals > 0 ? 'bg-amber-50 text-amber-600 border-amber-200' : 'bg-green-50 text-green-600 border-green-200', icon: '⏳' },
          { label: t.executiveDashboard.statWorkflows, value: activeWorkflows, color: 'bg-purple-50 text-purple-600 border-purple-200', icon: '⚡' },
          { label: t.executiveDashboard.statArOutstanding, value: totalAR, color: totalAR > 0 ? 'bg-emerald-50 text-emerald-600 border-emerald-200' : 'bg-gray-50 text-gray-600 border-gray-200', icon: '💰', isMoney: true },
          { label: t.executiveDashboard.statApOutstanding, value: totalAP, color: totalAP > 0 ? 'bg-orange-50 text-orange-600 border-orange-200' : 'bg-gray-50 text-gray-600 border-gray-200', icon: '📤', isMoney: true },
          { label: t.executiveDashboard.statDocuments, value: docStats?.total || 0, color: 'bg-indigo-50 text-indigo-600 border-indigo-200', icon: '📄' },
        ].map(s => (
          <div key={s.label} className={`rounded-xl border p-4 ${s.color}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-2xl">{s.icon}</span>
            </div>
            <p className="text-3xl font-bold">{s.isMoney ? `$${fmt(s.value)}` : s.value}</p>
            <p className="text-sm opacity-75 mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit overflow-x-auto">
        {([
          ['overview', t.executiveDashboard.tabOverview],
          ['attention', `${t.executiveDashboard.tabAttention} (${pendingApprovals + overdueInvoices.length + overdueBills.length})`],
          ['financial', t.executiveDashboard.tabFinancial],
          ['risks', `${t.executiveDashboard.tabRisks} (${risks.length})`],
          ['activity', t.executiveDashboard.tabActivity],
        ] as const).map(([key, label]) => (
          <button key={key} onClick={() => setActiveTab(key)} className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap ${activeTab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.executiveDashboard.quickNavigation}</h3>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Projects', icon: '🏗', page: 'projects' },
                { label: 'Procurement', icon: '🛒', page: 'procurements' },
                { label: 'Financial', icon: '💰', page: 'financial' },
                { label: 'Contracts', icon: '📋', page: 'contracts' },
                { label: 'Documents', icon: '📄', page: 'documents' },
                { label: 'Analytics', icon: '📊', page: 'analytics' },
                { label: 'AI Agents', icon: '🤖', page: 'ai' },
                { label: 'Builder', icon: '🔨', page: 'builder' },
              ].map(a => (
                <button key={a.page} className="flex items-center gap-2 p-3 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors text-left">
                  <span className="text-xl">{a.icon}</span>
                  <span className="text-sm font-medium text-gray-700">{a.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.executiveDashboard.businessObjects}</h3>
            {home && home.entity_counts.length > 0 ? (
              <div className="space-y-2">
                {home.entity_counts.sort((a, b) => b.count - a.count).slice(0, 8).map(ec => (
                  <div key={ec.entity_code} className="flex items-center gap-3">
                    <span className="text-sm text-gray-600 w-28 truncate">{ec.entity_code}</span>
                    <div className="flex-1 bg-gray-100 rounded-full h-2.5">
                      <div className="bg-blue-500 rounded-full h-2.5 transition-all" style={{ width: `${Math.min((ec.count / entityTotal) * 100, 100)}%` }} />
                    </div>
                    <span className="text-sm font-medium text-gray-900 w-8 text-right">{ec.count}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400 text-sm">{t.executiveDashboard.noDataYet}</p>
            )}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.executiveDashboard.recentEvents}</h3>
            {home && home.recent_events.length > 0 ? (
              <div className="space-y-2">
                {home.recent_events.slice(0, 8).map((ev, i) => {
                  const ts = ev.occurred_at || ev.created_at;
                  return (
                    <div key={i} className="flex items-center gap-3 py-1.5">
                      <div className="w-2 h-2 rounded-full bg-blue-400 shrink-0" />
                      <span className="text-sm text-gray-700 flex-1 truncate">{ev.event_type ?? ev.entity_type ?? 'event'}</span>
                      <span className="text-xs text-gray-400">{ts ? new Date(ts).toLocaleTimeString() : ''}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-gray-400 text-sm">{t.executiveDashboard.noEventsYet}</p>            )}
          </div>
        </div>
      )}

      {activeTab === 'attention' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.executiveDashboard.pendingApprovals}</h3>
            {approvals.length > 0 ? (
              <div className="space-y-3">
                {approvals.map(a => (
                  <div key={a.id} className="flex items-center justify-between p-3 bg-amber-50 rounded-lg border border-amber-200">
                    <div className="flex items-center gap-3">
                      <span className="text-xl">⏳</span>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{a.action}</p>
                        <p className="text-xs text-gray-500">{a.from_state} → {a.to_state}</p>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button className="px-3 py-1 bg-green-600 text-white text-xs rounded-lg hover:bg-green-700">{t.executiveDashboard.approve}</button>
                      <button className="px-3 py-1 bg-gray-200 text-gray-700 text-xs rounded-lg hover:bg-gray-300">{t.executiveDashboard.reject}</button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8"><p className="text-3xl mb-2">✅</p><p className="text-gray-500">{t.executiveDashboard.allClearNoApprovals}</p></div>
            )}
          </div>

          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.executiveDashboard.overdueInvoices}</h3>
              {overdueInvoices.length > 0 ? (
                <div className="space-y-2">
                  {overdueInvoices.slice(0, 5).map(inv => (
                    <div key={inv.id} className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-200">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{inv.invoice_number}</p>
                        <p className="text-xs text-gray-500">{t.executiveDashboard.due} {inv.due_date}</p>
                      </div>
                      <span className="text-sm font-bold text-red-600">${fmt(inv.balance_due)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4"><p className="text-gray-400 text-sm">{t.executiveDashboard.noOverdueInvoices}</p></div>
              )}
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.executiveDashboard.overdueBills}</h3>
              {overdueBills.length > 0 ? (
                <div className="space-y-2">
                  {overdueBills.slice(0, 5).map(bill => (
                    <div key={bill.id} className="flex items-center justify-between p-3 bg-orange-50 rounded-lg border border-orange-200">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{bill.bill_number}</p>
                        <p className="text-xs text-gray-500">{t.executiveDashboard.due} {bill.due_date}</p>
                      </div>
                      <span className="text-sm font-bold text-orange-600">${fmt(bill.balance_due)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4"><p className="text-gray-400 text-sm">{t.executiveDashboard.noOverdueBills}</p></div>
              )}
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.executiveDashboard.activeWorkflows}</h3>
              {home && home.workflows_needing_action.length > 0 ? (
                <div className="space-y-3">
                  {home.workflows_needing_action.map(w => (
                    <div key={w.instance_id} className="flex items-center gap-3 p-3 bg-purple-50 rounded-lg border border-purple-200">
                      <span className="text-xl">⚡</span>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">{w.workflow_code}</p>
                        <p className="text-xs text-gray-500">{t.executiveDashboard.state} {w.current_state}</p>
                      </div>
                      <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs">{w.status}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4"><p className="text-gray-400 text-sm">{t.executiveDashboard.noActiveWorkflows}</p></div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'financial' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">{t.executiveDashboard.arAging}</h3>
            {arAging ? (
              <div className="space-y-2">
                <div className="flex justify-between text-sm"><span className="text-gray-600">{t.executiveDashboard.current}</span><span className="font-medium text-green-600">${fmt(arAging.buckets.current || 0)}</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-600">1-30 days</span><span className="font-medium text-yellow-600">${fmt(arAging.buckets['1_30'] || 0)}</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-600">31-60 days</span><span className="font-medium text-orange-600">${fmt(arAging.buckets['31_60'] || 0)}</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-600">61-90 days</span><span className="font-medium text-red-600">${fmt(arAging.buckets['61_90'] || 0)}</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-600">90+ days</span><span className="font-bold text-red-700">${fmt(arAging.buckets['over_90'] || 0)}</span></div>
                <div className="flex justify-between py-2 border-t border-gray-200 mt-2 text-sm font-bold"><span>{t.executiveDashboard.totalAr}</span><span className="text-blue-600">${fmt(arAging.total_outstanding)}</span></div>
              </div>
            ) : <p className="text-gray-400 text-center py-4">{t.executiveDashboard.noData}</p>}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">{t.executiveDashboard.apAging}</h3>
            {apAging ? (
              <div className="space-y-2">
                <div className="flex justify-between text-sm"><span className="text-gray-600">{t.executiveDashboard.current}</span><span className="font-medium text-green-600">${fmt(apAging.buckets.current || 0)}</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-600">1-30 days</span><span className="font-medium text-yellow-600">${fmt(apAging.buckets['1_30'] || 0)}</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-600">31-60 days</span><span className="font-medium text-orange-600">${fmt(apAging.buckets['31_60'] || 0)}</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-600">61-90 days</span><span className="font-medium text-red-600">${fmt(apAging.buckets['61_90'] || 0)}</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-600">90+ days</span><span className="font-bold text-red-700">${fmt(apAging.buckets['over_90'] || 0)}</span></div>
                <div className="flex justify-between py-2 border-t border-gray-200 mt-2 text-sm font-bold"><span>{t.executiveDashboard.totalAp}</span><span className="text-orange-600">${fmt(apAging.total_outstanding)}</span></div>
              </div>
            ) : <p className="text-gray-400 text-center py-4">No data</p>}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.executiveDashboard.recentInvoices}</h3>
            <div className="space-y-2">
              {invoices.slice(0, 5).map(inv => (
                <div key={inv.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div><p className="text-sm font-medium text-gray-900">{inv.invoice_number}</p><p className="text-xs text-gray-500">{inv.issue_date}</p></div>
                  <div className="text-right"><p className="text-sm font-medium">${fmt(inv.total_amount)}</p><p className={`text-xs ${inv.balance_due > 0 ? 'text-red-600' : 'text-green-600'}`}>${fmt(inv.balance_due)} {t.executiveDashboard.dueAmount}</p></div>
                </div>
              ))}
              {invoices.length === 0 && <p className="text-gray-400 text-sm text-center py-4">{t.executiveDashboard.noInvoices}</p>}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.executiveDashboard.recentBills}</h3>
            <div className="space-y-2">
              {bills.slice(0, 5).map(bill => (
                <div key={bill.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div><p className="text-sm font-medium text-gray-900">{bill.bill_number}</p><p className="text-xs text-gray-500">{bill.issue_date}</p></div>
                  <div className="text-right"><p className="text-sm font-medium">${fmt(bill.total_amount)}</p><p className={`text-xs ${bill.balance_due > 0 ? 'text-red-600' : 'text-green-600'}`}>${fmt(bill.balance_due)} {t.executiveDashboard.dueAmount}</p></div>
                </div>
              ))}
              {bills.length === 0 && <p className="text-gray-400 text-sm text-center py-4">{t.executiveDashboard.noBills}</p>}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'risks' && (
        <div className="space-y-4">
          {risks.length > 0 ? risks.map((risk, i) => (
            <div key={i} className={`rounded-xl border p-4 ${risk.level === 'high' ? 'border-red-200 bg-red-50' : risk.level === 'medium' ? 'border-yellow-200 bg-yellow-50' : 'border-gray-200 bg-white'}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className={`w-3 h-3 rounded-full ${risk.level === 'high' ? 'bg-red-500' : risk.level === 'medium' ? 'bg-yellow-500' : 'bg-green-500'}`} />
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{risk.title}</p>
                    <p className="text-xs text-gray-500">{risk.detail}</p>
                  </div>
                </div>
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${risk.level === 'high' ? 'bg-red-100 text-red-800' : risk.level === 'medium' ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}`}>{risk.level}</span>
              </div>
              <p className="text-xs text-gray-600 mt-2 ml-6">{t.executiveDashboard.actionLabel} {risk.action}</p>
            </div>
          )) : (
            <div className="text-center py-12 text-gray-400"><p className="text-4xl mb-3">🛡️</p><p className="font-medium">{t.executiveDashboard.noDetectedRisks}</p><p className="text-sm">{t.executiveDashboard.allSystemsNormal}</p></div>
          )}
        </div>
      )}

      {activeTab === 'activity' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.executiveDashboard.recentEvents}</h3>
            {home && home.recent_events.length > 0 ? (
              <div className="space-y-2">
                {home.recent_events.map((ev, i) => {
                  const ts = ev.occurred_at || ev.created_at;
                  return (
                    <div key={i} className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0">
                      <div className="w-2 h-2 rounded-full bg-blue-400 shrink-0" />
                      <span className="text-sm text-gray-700 flex-1">{ev.event_type ?? ev.entity_type ?? 'event'}</span>
                      <span className="text-xs text-gray-400">{ts ? new Date(ts).toLocaleString() : ''}</span>
                    </div>
                  );
                })}
              </div>
            ) : <p className="text-gray-400 text-sm">No events yet.</p>}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.executiveDashboard.ruleActivity}</h3>
            {home && home.recent_rule_firings.length > 0 ? (
              <div className="space-y-2">
                {home.recent_rule_firings.map((r, i) => {
                  const ts = r.executed_at || r.fired_at;
                  return (
                    <div key={i} className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0">
                      <span className="w-2 h-2 rounded-full bg-purple-400 shrink-0" />
                      <span className="text-sm text-gray-700 flex-1">{r.rule_name || r.event_type || 'rule'}</span>
                      <span className="text-xs text-gray-400">{ts ? new Date(ts).toLocaleString() : ''}</span>
                    </div>
                  );
                })}
              </div>
            ) : <p className="text-gray-400 text-sm">{t.executiveDashboard.noRuleFirings}</p>}
          </div>
        </div>
      )}

      {docStats && docStats.total > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.executiveDashboard.documentIntelligence}</h3>
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: t.executiveDashboard.docTotal, value: docStats.total, color: 'text-blue-600' },
              { label: t.executiveDashboard.docProcessed, value: docStats.processed, color: 'text-green-600' },
              { label: t.executiveDashboard.docProcessing, value: docStats.processing, color: 'text-yellow-600' },
              { label: t.executiveDashboard.docFailed, value: docStats.failed, color: 'text-red-600' },
            ].map(s => (
              <div key={s.label} className="text-center">
                <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
                <p className="text-xs text-gray-500">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {projects.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.executiveDashboard.activeProjects}</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {projects.slice(0, 3).map(p => {
              const budget = parseFloat(p.budget || '0');
              return (
                <div key={p.id} className="p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-medium text-gray-900">{p.name}</p>
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${p.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>{p.status}</span>
                  </div>
                  <p className="text-xs text-gray-500">{p.client_name || t.executiveDashboard.noClient}</p>
                  <p className="text-xs font-medium text-blue-600 mt-1">{`$${(budget / 1000).toFixed(0)}K ${t.executiveDashboard.budgetSuffix}`}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
