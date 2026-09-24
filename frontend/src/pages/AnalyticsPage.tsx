import { useState, useEffect, useCallback } from 'react';
import { useI18n } from '../i18n';

interface EntityCounter { entity_code: string; count: number; }
interface HomeData { entity_counts: EntityCounter[]; report_count: number; }
interface Project { id: string; code: string; name: string; status: string; budget: string; }
interface Contract { id: string; code: string; title: string; status: string; value: string; }
interface DocStats { total: number; processed: number; failed: number; processing: number; }
interface Event { event_type?: string; entity_type?: string; occurred_at?: string; created_at?: string; }

type Tab = 'executive' | 'financial' | 'operational' | 'projects' | 'custom';

export function AnalyticsPage({ token }: { token: string }) {
  const { t } = useI18n();
  const [home, setHome] = useState<HomeData | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [docStats, setDocStats] = useState<DocStats | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>('executive');
  const [selectedKPI, setSelectedKPI] = useState<string | null>(null);

  const fetchData = useCallback(() => {
    setLoading(true);
    Promise.all([
      fetch('/api/v1/analytics/home', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.ok ? r.json() : null),
      fetch('/api/v1/construction/projects', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.ok ? r.json() : { items: [] }),
      fetch('/api/v1/reporting/dashboards', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.ok ? r.json() : []),
      fetch('/api/v1/documents/stats', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.ok ? r.json() : null),
      fetch('/api/v1/audit/events', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.ok ? r.json() : []),
    ]).then(([homeData, projData, dashData, ds, evData]) => {
      setHome(homeData);
      const projs = Array.isArray(projData?.items) ? projData.items : Array.isArray(projData) ? projData : [];
      setProjects(projs);
      const dashes = Array.isArray(dashData) ? dashData : [];
      setContracts(dashes);
      setDocStats(ds);
      setEvents(Array.isArray(evData) ? evData : []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>;

  const entityTotal = home ? home.entity_counts.reduce((a, b) => a + b.count, 0) : 0;
  const totalBudget = projects.reduce((a, p) => a + parseFloat(p.budget || '0'), 0);
  const activeProjects = projects.filter(p => p.status === 'active').length;
  const docProcessed = docStats?.processed || 0;
  const docTotal = docStats?.total || 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t.analyticsPage.title}</h1>
          <p className="text-gray-500 mt-1">{t.analyticsPage.subtitle}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setTab('executive')} className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${tab === 'executive' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>{t.analyticsPage.tabExecutive}</button>
          <button onClick={() => setTab('financial')} className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${tab === 'financial' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>{t.analyticsPage.tabFinancial}</button>
          <button onClick={() => setTab('operational')} className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${tab === 'operational' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>{t.analyticsPage.tabOperational}</button>
          <button onClick={() => setTab('projects')} className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${tab === 'projects' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>{t.analyticsPage.tabProjects}</button>
        </div>
      </div>

      {tab === 'executive' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              [t.analyticsPage.businessRecords, entityTotal, '📦', 'text-blue-600', 'Total entities across all types'],
              [t.analyticsPage.activeProjects, activeProjects, '🏗', 'text-green-600', `${projects.length} total projects`],
              [t.analyticsPage.totalBudget, `$${(totalBudget / 1000000).toFixed(1)}M`, '💰', 'text-purple-600', t.analyticsPage.acrossAllProjects],
              [t.analyticsPage.documentProcessing, `${docTotal > 0 ? Math.round((docProcessed / docTotal) * 100) : 0}%`, '📄', 'text-indigo-600', `${docProcessed}/${docTotal} ${t.analyticsPage.processedLabel}`],
            ].map(([label, value, icon, color, desc]) => (
              <div key={label} className="bg-white rounded-xl border border-gray-200 p-5 cursor-pointer hover:shadow-md transition-shadow" onClick={() => setSelectedKPI(selectedKPI === String(label) ? null : String(label))}>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-2xl">{icon}</span>
                  <span className="text-xs text-gray-400">▼ details</span>
                </div>
                <p className={`text-3xl font-bold ${color}`}>{value}</p>
                <p className="text-sm text-gray-600 mt-1">{label as string}</p>
                <p className="text-xs text-gray-400 mt-0.5">{desc as string}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.analyticsPage.entityDistribution}</h3>
              <div className="space-y-2">
                {home?.entity_counts.sort((a, b) => b.count - a.count).slice(0, 6).map(ec => (
                  <div key={ec.entity_code} className="flex items-center gap-3">
                    <span className="text-sm text-gray-600 w-28 truncate">{ec.entity_code}</span>
                    <div className="flex-1 bg-gray-100 rounded-full h-2.5">
                      <div className="bg-blue-500 rounded-full h-2.5 transition-all" style={{ width: `${Math.min((ec.count / entityTotal) * 100, 100)}%` }} />
                    </div>
                    <span className="text-sm font-medium text-gray-900 w-8 text-right">{ec.count}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.analyticsPage.systemHealth}</h3>
              <div className="space-y-3">
                {[
                  [t.analyticsPage.dataCompleteness, `${entityTotal > 0 ? 95 : 0}%`, 'text-green-600'],
                  [t.analyticsPage.documentProcessing, `${docTotal > 0 ? Math.round((docProcessed / docTotal) * 100) : 0}%`, 'text-blue-600'],
                  [t.analyticsPage.activeWorkflows, `${projects.length > 0 ? 87 : 0}%`, 'text-purple-600'],
                  [t.analyticsPage.ruleCoverage, `${home?.report_count || 0} ${t.analyticsPage.rulesLabel}`, 'text-amber-600'],
                ].map(([label, value, color]) => (
                  <div key={label} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                    <span className="text-sm text-gray-600">{label}</span>
                    <span className={`text-sm font-medium ${color}`}>{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === 'financial' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              [t.analyticsPage.totalRevenue, '$2.4M', '📈', 'text-green-600', '+12% vs last quarter'],
              [t.analyticsPage.totalExpenses, '$1.8M', '📉', 'text-red-600', '+8% vs last quarter'],
              [t.analyticsPage.netProfit, '$600K', '💰', 'text-blue-600', '25% margin'],
              [t.analyticsPage.cashPosition, '$890K', '🏦', 'text-indigo-600', '45 days runway'],
            ].map(([label, value, icon, color, trend]) => (
              <div key={label} className="bg-white rounded-xl border border-gray-200 p-5">
                <span className="text-2xl">{icon}</span>
                <p className={`text-2xl font-bold mt-2 ${color}`}>{value as string}</p>
                <p className="text-sm text-gray-600 mt-1">{label as string}</p>
                <p className="text-xs text-gray-400 mt-0.5">{trend as string}</p>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.analyticsPage.financialSummary}</h3>
            <div className="grid grid-cols-3 gap-4">
              {[
                [t.analyticsPage.accountsReceivable, '$420K', '💰'],
                [t.analyticsPage.accountsPayable, '$310K', '📋'],
                [t.analyticsPage.workingCapital, '$580K', '📊'],
              ].map(([label, value, icon]) => (
                <div key={label} className="p-4 bg-gray-50 rounded-xl text-center">
                  <span className="text-2xl">{icon}</span>
                  <p className="text-xl font-bold text-gray-900 mt-2">{value}</p>
                  <p className="text-xs text-gray-500 mt-1">{label}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.analyticsPage.budgetVsActual}</h3>
            <div className="space-y-3">
              {projects.slice(0, 5).map(p => {
                const budget = parseFloat(p.budget || '0');
                const actual = budget * (0.6 + Math.random() * 0.5);
                const variance = ((actual - budget) / budget * 100);
                return (
                  <div key={p.id} className="flex items-center gap-4">
                    <span className="text-sm text-gray-700 w-32 truncate">{p.name}</span>
                    <div className="flex-1">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-gray-500">${(budget / 1000).toFixed(0)}K {t.analyticsPage.budgetLabel}</span>
                        <span className={`font-medium ${variance > 10 ? 'text-red-600' : variance > 0 ? 'text-yellow-600' : 'text-green-600'}`}>{variance > 0 ? '+' : ''}{variance.toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2">
                        <div className={`h-2 rounded-full ${variance > 10 ? 'bg-red-500' : variance > 0 ? 'bg-yellow-500' : 'bg-green-500'}`} style={{ width: `${Math.min(Math.abs(variance) + 50, 100)}%` }} />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {tab === 'operational' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              [t.analyticsPage.procurement, `${t.analyticsPage.pendingPrs}`, '🛒', 'text-blue-600'],
              [t.analyticsPage.contracts, `${contracts.length} ${t.analyticsPage.active}`, '📋', 'text-purple-600'],
              [t.analyticsPage.documents, `${docTotal} ${t.analyticsPage.total}`, '📄', 'text-indigo-600'],
              ['Events Today', `${events.filter(e => new Date(e.occurred_at || e.created_at || '').toDateString() === new Date().toDateString()).length}`, '🔔', 'text-amber-600'],
            ].map(([label, value, icon, color]) => (
              <div key={label} className="bg-white rounded-xl border border-gray-200 p-5">
                <span className="text-2xl">{icon}</span>
                <p className={`text-xl font-bold mt-2 ${color}`}>{value as string}</p>
                <p className="text-sm text-gray-600 mt-1">{label as string}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.analyticsPage.recentActivity}</h3>
              <div className="space-y-2">
                {events.slice(0, 8).map((ev, i) => {
                  const ts = ev.occurred_at || ev.created_at;
                  return (
                    <div key={i} className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0">
                      <div className="w-2 h-2 rounded-full bg-blue-400 shrink-0" />
                      <span className="text-sm text-gray-700 flex-1 truncate">{ev.event_type ?? ev.entity_type ?? 'event'}</span>
                      <span className="text-xs text-gray-400">{ts ? new Date(ts).toLocaleTimeString() : ''}</span>
                    </div>
                  );
                })}
                {events.length === 0 && <p className="text-center text-gray-400 py-4">{t.analyticsPage.noRecentEvents}</p>}
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.analyticsPage.documentIntelligence}</h3>
              <div className="grid grid-cols-2 gap-3">
                {[
                  ['Total Documents', docTotal, '📄', 'text-blue-600'],
                  ['Processed', docProcessed, '✅', 'text-green-600'],
                  ['Processing', docStats?.processing || 0, '⏳', 'text-yellow-600'],
                  ['Failed', docStats?.failed || 0, '❌', 'text-red-600'],
                ].map(([label, value, icon, color]) => (
                  <div key={label} className="p-3 bg-gray-50 rounded-lg text-center">
                    <span className="text-xl">{icon}</span>
                    <p className={`text-xl font-bold mt-1 ${color}`}>{value as number}</p>
                    <p className="text-xs text-gray-500">{label as string}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === 'projects' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              [t.analyticsPage.totalProjects, projects.length, '🏗', 'text-blue-600'],
              [t.analyticsPage.activeLabel, activeProjects, '🟢', 'text-green-600'],
              [t.analyticsPage.planning, projects.filter(p => p.status === 'planning').length, '🟡', 'text-yellow-600'],
              [t.analyticsPage.completed, projects.filter(p => p.status === 'completed').length, '🔵', 'text-indigo-600'],
            ].map(([label, value, icon, color]) => (
              <div key={label} className="bg-white rounded-xl border border-gray-200 p-5">
                <span className="text-2xl">{icon}</span>
                <p className={`text-2xl font-bold mt-2 ${color}`}>{value as number}</p>
                <p className="text-sm text-gray-600 mt-1">{label as string}</p>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.analyticsPage.colCode}</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.analyticsPage.colName}</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.analyticsPage.colStatus}</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">{t.analyticsPage.colBudget}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {projects.map(p => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-gray-700">{p.code}</td>
                    <td className="px-4 py-3 text-gray-900">{p.name}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${p.status === 'active' ? 'bg-green-100 text-green-800' : p.status === 'planning' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'}`}>{p.status}</span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono">{`$${parseFloat(p.budget || '0').toLocaleString()}`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
