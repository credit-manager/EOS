import { useState, useEffect } from 'react';
import { TranslationKeys } from '../i18n';
import { api } from '../api';

interface Project {
  id: string;
  code: string;
  name: string;
  status: string;
  budget: string;
  spent: string;
  client_name: string;
  location: string;
  start_date: string;
  end_date: string;
  description: string;
  project_manager: string;
  progress: number;
  created_at: string;
}

interface Contract {
  id: string;
  code: string;
  title: string;
  status: string;
  value: string;
  project_id: string;
}

interface BOQItem {
  id: string;
  item_code: string;
  description: string;
  quantity: string;
  unit_price: string;
  total_price: string;
  status: string;
}

interface Claim {
  id: string;
  claim_number: string;
  title: string;
  status: string;
  amount: string;
  project_id: string;
}

interface PurchaseRequest {
  id: string;
  pr_number: string;
  description: string;
  status: string;
  estimated_cost: string;
  project_id: string;
}

type Tab = 'overview' | 'financial' | 'budget' | 'contracts' | 'procurement' | 'documents' | 'timeline' | 'risks' | 'approvals' | 'ai';

export default function ProjectsPage({ t, token }: { t: TranslationKeys; token: string }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [tab, setTab] = useState<Tab>('overview');
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [boqItems, setBoqItems] = useState<BOQItem[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [purchaseRequests, setPurchaseRequests] = useState<PurchaseRequest[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({ code: '', name: '', status: 'planning', budget: '', client_name: '', location: '', description: '', start_date: '', end_date: '' });
  const [aiQuery, setAiQuery] = useState('');
  const [aiResponse, setAiResponse] = useState<string | null>(null);

  useEffect(() => {
    fetchProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedProject) {
      Promise.all([
        api<Contract[]>(`/construction/projects/${selectedProject.id}/contracts`, token).catch(() => []),
        api<BOQItem[]>(`/construction/projects/${selectedProject.id}/boq`, token).catch(() => []),
        api<Claim[]>(`/construction/claims?project_id=${selectedProject.id}`, token).catch(() => []),
        api<PurchaseRequest[]>(`/procurement/requests?project_id=${selectedProject.id}`, token).catch(() => []),
      ]).then(([c, b, cl, pr]) => {
        setContracts(Array.isArray(c) ? c : []);
        setBoqItems(Array.isArray(b) ? b : []);
        setClaims(Array.isArray(cl) ? cl : []);
        setPurchaseRequests(Array.isArray(pr) ? pr : []);
      });
    }
  }, [selectedProject, token]);

  const fetchProjects = async () => {
    try {
      const response = await fetch('/api/v1/construction/projects', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setProjects(data.items || data);
      }
    } catch { setError(t.common.error); }
    finally { setLoading(false); }
  };

  const handleCreate = async () => {
    setError(null);
    try {
      const response = await fetch('/api/v1/construction/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(formData),
      });
      if (response.ok) {
        setShowCreate(false);
        setFormData({ code: '', name: '', status: 'planning', budget: '', client_name: '', location: '', description: '', start_date: '', end_date: '' });
        fetchProjects();
      } else {
        const data = await response.json();
        setError(data.detail || t.common.error);
      }
    } catch { setError(t.common.error); }
  };

  const handleAskAboutProject = async () => {
    if (!aiQuery.trim() || !selectedProject) return;
    setAiResponse(null);
    try {
      const r = await fetch('/api/v1/ai/execute', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_code: 'project_agent', input: { query: aiQuery, project_id: selectedProject.id, project_name: selectedProject.name, budget: selectedProject.budget } }),
      });
      if (r.ok) { const d = await r.json(); setAiResponse(d.output?.response || 'Analysis complete.'); }
      else { setAiResponse('Analysis feature is being initialized.'); }
    } catch { setAiResponse('AI engine connecting...'); }
    setAiQuery('');
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>;

  if (!selectedProject) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">{t.projects.title}</h1>
          <button onClick={() => setShowCreate(!showCreate)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">{showCreate ? t.common.cancel : t.projectsPage.newProject}</button>
        </div>
        {error && <div className="px-4 py-2 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}
        {showCreate && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-3">{t.projectsPage.newProject}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {([
                ['code', t.projectsPage.code],
                ['name', t.projectsPage.name],
                ['budget', t.projectsPage.budget],
                ['client_name', t.projectsPage.client],
                ['location', t.projectsPage.location],
                ['description', t.projectsPage.description]
              ] as const).map(([field, label]) => (
                <div key={field}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                  <input type={field === 'budget' ? 'number' : 'text'} value={formData[field]} onChange={e => setFormData({ ...formData, [field]: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" />
                </div>
              ))}
            </div>
            <button onClick={handleCreate} className="mt-3 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">{t.projectsPage.save}</button>
          </div>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map(project => {
            const budget = parseFloat(project.budget || '0');
            const spent = parseFloat(project.spent || '0');
            const utilization = budget > 0 ? Math.round((spent / budget) * 100) : 0;
            return (
              <div key={project.id} onClick={() => setSelectedProject(project)} className="bg-white rounded-xl border border-gray-200 p-5 cursor-pointer hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="text-xs text-gray-400 font-mono">{project.code}</p>
                    <h3 className="text-lg font-bold text-gray-900">{project.name}</h3>
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${project.status === 'active' ? 'bg-green-100 text-green-800' : project.status === 'planning' ? 'bg-yellow-100 text-yellow-800' : project.status === 'completed' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'}`}>{project.status}</span>
                </div>
                <p className="text-sm text-gray-500 mb-3">{project.client_name || t.projectsPage.noClient}</p>
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span>{project.location || '—'}</span>
                </div>
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-500">{t.projectsPage.budgetUtilization}</span>
                    <span className={`font-medium ${utilization > 90 ? 'text-red-600' : utilization > 70 ? 'text-yellow-600' : 'text-green-600'}`}>{utilization}%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-1.5">
                    <div className={`h-1.5 rounded-full ${utilization > 90 ? 'bg-red-500' : utilization > 70 ? 'bg-yellow-500' : 'bg-green-500'}`} style={{ width: `${Math.min(utilization, 100)}%` }} />
                  </div>
                </div>
              </div>
            );
          })}
          {projects.length === 0 && <p className="text-center text-gray-400 py-8 col-span-3">{t.projectsPage.noProjects}</p>}
        </div>
      </div>
    );
  }

  const budget = parseFloat(selectedProject.budget || '0');
  const spent = parseFloat(selectedProject.spent || '0');
  const utilization = budget > 0 ? Math.round((spent / budget) * 100) : 0;
  const contractTotal = contracts.reduce((a, c) => a + parseFloat(c.value || '0'), 0);
  const claimTotal = claims.reduce((a, c) => a + parseFloat(c.amount || '0'), 0);
  const prTotal = purchaseRequests.reduce((a, pr) => a + parseFloat(pr.estimated_cost || '0'), 0);

  return (
    <div className="space-y-6">
      {/* Project Header */}
      <div className="flex items-center gap-4">
        <button onClick={() => setSelectedProject(null)} className="text-gray-500 hover:text-gray-700 text-sm">&larr; {t.projects.title}</button>
        <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center text-white text-xl font-bold">{selectedProject.code[0]?.toUpperCase()}</div>
        <div className="flex-1">
          <h2 className="text-2xl font-bold text-gray-900">{selectedProject.name}</h2>
          <p className="text-gray-500 text-sm">{selectedProject.client_name} &middot; {selectedProject.location}</p>
        </div>
        <span className={`px-3 py-1 text-sm font-medium rounded-full ${selectedProject.status === 'active' ? 'bg-green-100 text-green-800' : selectedProject.status === 'planning' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'}`}>{selectedProject.status}</span>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-5 gap-4">
        {[
          { label: t.projectsPage.budget, value: `$${(budget / 1000).toFixed(0)}K`, icon: '💰', color: 'text-blue-600' },
          { label: t.projectsPage.spentStat, value: `$${(spent / 1000).toFixed(0)}K`, icon: '📊', color: utilization > 90 ? 'text-red-600' : 'text-green-600' },
          { label: t.projectsPage.contractsStat, value: contracts.length, icon: '📋', color: 'text-purple-600' },
          { label: t.projectsPage.claimsStat, value: `$${(claimTotal / 1000).toFixed(0)}K`, icon: '📑', color: 'text-orange-600' },
          { label: t.projectsPage.procurementStat, value: purchaseRequests.length, icon: '🛒', color: 'text-indigo-600' },
        ].map(s => (
          <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-4 text-center">
            <span className="text-xl">{s.icon}</span>
            <p className={`text-2xl font-bold mt-1 ${s.color}`}>{s.value}</p>
            <p className="text-xs text-gray-500">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit overflow-x-auto">
        {([
          ['overview', t.projectsPage.overview],
          ['financial', t.projectsPage.financial],
          ['budget', t.projectsPage.budget],
          ['contracts', `${t.projectsPage.contracts} (${contracts.length})`],
          ['procurement', `${t.projectsPage.procurement} (${purchaseRequests.length})`],
          ['documents', t.projectsPage.documents],
          ['timeline', t.projectsPage.timeline],
          ['risks', t.projectsPage.risks],
          ['approvals', t.projectsPage.approvals],
          ['ai', t.projectsPage.aiInsights],
        ] as const).map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)} className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap ${tab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>{label}</button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.projectsPage.projectInformation}</h3>
            <div className="space-y-2">
              {([[t.projectsPage.code, selectedProject.code], [t.projectsPage.client, selectedProject.client_name], [t.projectsPage.location, selectedProject.location], [t.projectsPage.manager, selectedProject.project_manager || '—'], [t.projectsPage.start, selectedProject.start_date || '—'], [t.projectsPage.end, selectedProject.end_date || '—']].map(([k, v]) => (
                <div key={k} className="flex justify-between py-2 border-b border-gray-100"><span className="text-sm text-gray-500">{k}</span><span className="text-sm font-medium">{v}</span></div>
              )))}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.projectsPage.progress}</h3>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs mb-1"><span className="text-gray-500">{t.projectsPage.completion}</span><span className="font-medium">{selectedProject.progress || 0}%</span></div>
                <div className="w-full bg-gray-100 rounded-full h-2"><div className="bg-blue-500 h-2 rounded-full" style={{ width: `${selectedProject.progress || 0}%` }} /></div>
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1"><span className="text-gray-500">{t.projectsPage.budgetUsed}</span><span className={`font-medium ${utilization > 90 ? 'text-red-600' : 'text-green-600'}`}>{utilization}%</span></div>
                <div className="w-full bg-gray-100 rounded-full h-2"><div className={`h-2 rounded-full ${utilization > 90 ? 'bg-red-500' : utilization > 70 ? 'bg-yellow-500' : 'bg-green-500'}`} style={{ width: `${Math.min(utilization, 100)}%` }} /></div>
              </div>
              <div className="grid grid-cols-2 gap-3 pt-2">
                {[
                  [t.projectsPage.contracts, contracts.length.toString()],
                  [t.projectsPage.claimsStat, claims.length.toString()],
                  [t.projectsPage.purchaseRequests, purchaseRequests.length.toString()],
                  [t.projectsPage.boqItems, boqItems.length.toString()],
                ].map(([k, v]) => (
                  <div key={k} className="p-3 bg-gray-50 rounded-lg"><p className="text-xs text-gray-500">{k}</p><p className="text-lg font-bold text-gray-900">{v}</p></div>
                ))}
              </div>
            </div>
          </div>
          {selectedProject.description && (
            <div className="bg-white rounded-xl border border-gray-200 p-5 lg:col-span-2">
              <h3 className="text-sm font-semibold text-gray-900 mb-2">{t.projectsPage.description}</h3>
              <p className="text-sm text-gray-600">{selectedProject.description}</p>
            </div>
          )}
        </div>
      )}

      {tab === 'financial' && (
        <div className="space-y-6">
          <div className="grid grid-cols-4 gap-4">
            {[
              [t.projectsPage.totalBudget, `$${(budget / 1000).toFixed(0)}K`, 'text-blue-600'],
              [t.projectsPage.contractValue, `$${(contractTotal / 1000).toFixed(0)}K`, 'text-purple-600'],
              [t.projectsPage.claimsFiled, `$${(claimTotal / 1000).toFixed(0)}K`, 'text-orange-600'],
              [t.projectsPage.prEstimated, `$${(prTotal / 1000).toFixed(0)}K`, 'text-indigo-600'],
            ].map(([k, v, c]) => (
              <div key={k} className="bg-white rounded-xl border border-gray-200 p-4">
                <p className="text-xs text-gray-500">{k}</p>
                <p className={`text-2xl font-bold mt-1 ${c}`}>{v}</p>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.projectsPage.financialBreakdown}</h3>
            <div className="space-y-2">
              {contracts.map(c => (
                <div key={c.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <div><p className="text-sm font-medium text-gray-900">{c.title}</p><p className="text-xs text-gray-500">{c.code}</p></div>
                  <div className="text-right"><p className="text-sm font-medium">{`$${parseFloat(c.value || '0').toLocaleString()}`}</p><p className={`text-xs ${c.status === 'active' ? 'text-green-600' : 'text-gray-500'}`}>{c.status}</p></div>
                </div>
              ))}
              {contracts.length === 0 && <p className="text-center text-gray-400 py-4">{t.projectsPage.noContractsLinked}</p>}
            </div>
          </div>
        </div>
      )}

      {tab === 'budget' && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.projectsPage.budgetAllocation}</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center p-4 bg-blue-50 rounded-lg"><span className="text-sm font-medium text-blue-900">{t.projectsPage.totalBudget}</span><span className="text-lg font-bold text-blue-900">{`$${budget.toLocaleString()}`}</span></div>
              <div className="flex justify-between items-center p-4 bg-red-50 rounded-lg"><span className="text-sm font-medium text-red-900">{t.projectsPage.spentStat}</span><span className="text-lg font-bold text-red-900">{`$${spent.toLocaleString()}`}</span></div>
              <div className="flex justify-between items-center p-4 bg-green-50 rounded-lg"><span className="text-sm font-medium text-green-900">{t.projectsPage.remaining}</span><span className="text-lg font-bold text-green-900">{`$${(budget - spent).toLocaleString()}`}</span></div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.projectsPage.boqSummary}</h3>
            <div className="space-y-2">
              {boqItems.map(item => (
                <div key={item.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <div><p className="text-sm font-medium text-gray-900">{item.description}</p><p className="text-xs text-gray-500">{item.item_code} &middot; {item.quantity} units</p></div>
                  <div className="text-right"><p className="text-sm font-medium">{`$${parseFloat(item.total_price || '0').toLocaleString()}`}</p><p className={`text-xs ${item.status === 'completed' ? 'text-green-600' : 'text-gray-500'}`}>{item.status}</p></div>
                </div>
              ))}
              {boqItems.length === 0 && <p className="text-center text-gray-400 py-4">{t.projectsPage.noBoqItems}</p>}
            </div>
          </div>
        </div>
      )}

      {tab === 'contracts' && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.projectsPage.code}</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.projectsPage.title}</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.projectsPage.status}</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">{t.projectsPage.value}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {contracts.map(c => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-gray-700">{c.code}</td>
                    <td className="px-4 py-3 text-gray-900">{c.title}</td>
                    <td className="px-4 py-3"><span className={`px-2 py-1 text-xs font-medium rounded-full ${c.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>{c.status}</span></td>
                    <td className="px-4 py-3 text-right font-mono">{`$${parseFloat(c.value || '0').toLocaleString()}`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {contracts.length === 0 && <div className="text-center py-8 text-gray-400">{t.projectsPage.noContractsLinkedToProject}</div>}
        </div>
      )}

      {tab === 'procurement' && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.projectsPage.prNumber}</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.projectsPage.description}</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.projectsPage.status}</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">{t.projectsPage.estCost}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {purchaseRequests.map(pr => (
                  <tr key={pr.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-gray-700">{pr.pr_number}</td>
                    <td className="px-4 py-3 text-gray-900">{pr.description}</td>
                    <td className="px-4 py-3"><span className={`px-2 py-1 text-xs font-medium rounded-full ${pr.status === 'approved' ? 'bg-green-100 text-green-800' : pr.status === 'pending' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'}`}>{pr.status}</span></td>
                    <td className="px-4 py-3 text-right font-mono">{`$${parseFloat(pr.estimated_cost || '0').toLocaleString()}`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {purchaseRequests.length === 0 && <div className="text-center py-8 text-gray-400">{t.projectsPage.noPurchaseRequests}</div>}
        </div>
      )}

      {tab === 'documents' && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <p className="text-4xl mb-3">📄</p>
          <p className="text-gray-500 font-medium">{t.projectsPage.documentIntelligence}</p>
          <p className="text-sm text-gray-400 mt-1">{t.projectsPage.documentHint}</p>
          <div className="flex justify-center gap-3 mt-4">
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">{t.projectsPage.uploadDocument}</button>
            <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200">{t.projectsPage.viewAll}</button>
          </div>
        </div>
      )}

      {tab === 'timeline' && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.projectsPage.projectTimeline}</h3>
          <div className="space-y-3">
            {[
              { title: t.projectsPage.projectCreated, date: selectedProject.created_at, icon: '🏁', color: 'bg-blue-100 text-blue-600' },
              ...contracts.map(c => ({ title: `${t.projectsPage.contract}: ${c.title}`, date: '', icon: '📋', color: 'bg-purple-100 text-purple-600' })),
              ...claims.map(c => ({ title: `${t.projectsPage.claim}: ${c.title}`, date: '', icon: '📑', color: 'bg-orange-100 text-orange-600' })),
              ...purchaseRequests.map(pr => ({ title: `${t.projectsPage.pr}: ${pr.pr_number}`, date: '', icon: '🛒', color: 'bg-indigo-100 text-indigo-600' })),
            ].map((item, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className={`w-8 h-8 ${item.color} rounded-full flex items-center justify-center text-sm shrink-0`}>{item.icon}</div>
                <div className="flex-1 pb-3 border-b border-gray-100 last:border-0">
                  <p className="text-sm font-medium text-gray-900">{item.title}</p>
                  {item.date && <p className="text-xs text-gray-500">{new Date(item.date).toLocaleDateString()}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'risks' && (
        <div className="space-y-4">
          {[
            { title: t.projectsPage.budgetOverrun, level: utilization > 90 ? 'high' : utilization > 70 ? 'medium' : 'low', detail: `${utilization}% budget utilized`, action: utilization > 90 ? 'Review spending immediately' : 'Monitor closely' },
            { title: t.projectsPage.claimsPending, level: claims.length > 2 ? 'high' : claims.length > 0 ? 'medium' : 'low', detail: `${claims.length} active claims`, action: claims.length > 0 ? 'Review claim status' : 'No action needed' },
            { title: t.projectsPage.procurementBottleneck, level: purchaseRequests.filter(pr => pr.status === 'pending').length > 3 ? 'high' : 'low', detail: `${purchaseRequests.filter(pr => pr.status === 'pending').length} pending PRs`, action: t.projectsPage.pendingApprovals },
          ].map(risk => (
            <div key={risk.title} className={`bg-white rounded-xl border p-4 ${risk.level === 'high' ? 'border-red-200 bg-red-50' : risk.level === 'medium' ? 'border-yellow-200 bg-yellow-50' : 'border-gray-200'}`}>
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
              <p className="text-xs text-gray-600 mt-2 ml-6">Action: {risk.action}</p>
            </div>
          ))}
        </div>
      )}

      {tab === 'approvals' && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <p className="text-4xl mb-3">⏳</p>
          <p className="text-gray-500 font-medium">{t.projectsPage.pendingApprovals}</p>
          <p className="text-sm text-gray-400 mt-1">{t.projectsPage.approvalsHint}</p>
        </div>
      )}

      {tab === 'ai' && (
        <div className="space-y-4">
          <div className="bg-gradient-to-r from-indigo-600 to-purple-700 rounded-2xl p-6 text-white">
            <h3 className="font-bold text-lg mb-2">{t.projectsPage.aiProjectAnalyst}</h3>
            <p className="text-indigo-100 text-sm mb-4">{t.projectsPage.aiProjectDesc}</p>
            <div className="flex gap-3">
              <input type="text" value={aiQuery} onChange={e => setAiQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleAskAboutProject()} placeholder={t.projectsPage.aiPlaceholder} className="flex-1 px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-indigo-200 focus:outline-none" />
              <button onClick={handleAskAboutProject} className="px-6 py-3 bg-white text-indigo-700 font-semibold rounded-xl hover:bg-indigo-50">{t.projectsPage.ask}</button>
            </div>
          </div>
          {aiResponse && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-sm text-gray-700 leading-relaxed">{aiResponse}</p>
            </div>
          )}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {['Budget analysis', 'Risk assessment', 'Timeline review', 'Procurement status'].map(q => (
              <button key={q} onClick={() => setAiQuery(q)} className="p-3 bg-white border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50 text-left">{q}</button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
