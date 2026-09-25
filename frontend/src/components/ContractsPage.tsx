import { useState, useEffect } from 'react';
import { useI18n } from '../i18n';

interface Contract {
  id: string;
  contract_number: string;
  project_id: string;
  project_name: string;
  contract_type: string;
  title: string;
  counterparty: string;
  contract_value: string;
  status: string;
  signed_date: string;
  completion_date: string;
  created_at: string;
}

type Tab = 'overview' | 'financial' | 'timeline' | 'documents' | 'risks' | 'ai';

export default function ContractsPage({ token }: { token: string }) {
  const { t } = useI18n();
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedContract, setSelectedContract] = useState<Contract | null>(null);
  const [tab, setTab] = useState<Tab>('overview');
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({ contract_number: '', project_id: '', contract_type: 'main', title: '', counterparty: '', contract_value: '', status: 'draft', signed_date: '', completion_date: '' });
  const [aiQuery, setAiQuery] = useState('');
  const [aiResponse, setAiResponse] = useState<string | null>(null);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { fetchContracts(); }, []);

  const fetchContracts = async () => {
    try {
      const response = await fetch('/api/v1/construction/contracts', { headers: { Authorization: `Bearer ${token}` } });
      if (response.ok) {
        const data = await response.json();
        const items = data.items || data;
        setContracts((Array.isArray(items) ? items : []).map((c: Record<string, unknown>) => ({
          id: String(c.id ?? ''), contract_number: String(c.contract_number ?? ''), project_id: String(c.project_id ?? ''),
          contract_type: String(c.contract_type ?? 'main'), title: String(c.title ?? ''), counterparty: String(c.counterparty ?? ''),
          contract_value: String(c.contract_value ?? ''), status: String(c.status ?? 'draft'), project_name: String(c.project_name ?? ''),
          signed_date: String(c.signed_date ?? ''), completion_date: String(c.completion_date ?? ''), created_at: String(c.created_at ?? ''),
        })));
      }
    } catch { setError(t.common.error); } finally { setLoading(false); }
  };

  const handleCreate = async () => {
    setError(null);
    try {
      const response = await fetch('/api/v1/construction/contracts', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(formData),
      });
      if (response.ok) { setShowCreate(false); setFormData({ contract_number: '', project_id: '', contract_type: 'main', title: '', counterparty: '', contract_value: '', status: 'draft', signed_date: '', completion_date: '' }); fetchContracts(); }
      else { const data = await response.json(); setError(data.detail || t.common.error); }
    } catch { setError(t.common.error); }
  };

  const handleAskAboutContract = async () => {
    if (!aiQuery.trim() || !selectedContract) return;
    setAiResponse(null);
    try {
      const r = await fetch('/api/v1/ai/execute', {
        method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_code: 'executive_agent', input: { query: aiQuery, contract: selectedContract.title, value: selectedContract.contract_value } }),
      });
      if (r.ok) { const d = await r.json(); setAiResponse(d.output?.response || t.contractsPage.analysisComplete); }
      else { setAiResponse(t.contractsPage.analysisInitializing); }
    } catch { setAiResponse(t.contractsPage.aiConnecting); }
    setAiQuery('');
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>;

  if (!selectedContract) {
    const totalValue = contracts.reduce((a, c) => a + parseFloat(c.contract_value || '0'), 0);
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{t.contracts.title}</h1>
            <p className="text-gray-500 mt-1">{contracts.length} {t.contractsPage.contractsCount} &middot; ${totalValue.toLocaleString()} {t.contractsPage.totalValueLabel}</p>
          </div>
          <button onClick={() => setShowCreate(!showCreate)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">{showCreate ? t.common.cancel : `+ ${t.contractsPage.newContract}`}</button>
        </div>
        {error && <div className="px-4 py-2 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}
        {showCreate && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-3">{t.contractsPage.newContract}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {([
                { field: 'contract_number' as const, label: t.contractsPage.contractNumber },
                { field: 'title' as const, label: t.contractsPage.titleField },
                { field: 'counterparty' as const, label: t.contractsPage.counterpartyField },
                { field: 'contract_value' as const, label: t.contractsPage.contractValue },
              ]).map(({ field, label }) => (
                <div key={field}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                  <input type={field === 'contract_value' ? 'number' : 'text'} value={formData[field]} onChange={e => setFormData({ ...formData, [field]: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" />
                </div>
              ))}
            </div>
            <button onClick={handleCreate} className="mt-3 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">{t.common.save}</button>
          </div>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {contracts.map(contract => {
            const value = parseFloat(contract.contract_value || '0');
            return (
              <div key={contract.id} onClick={() => setSelectedContract(contract)} className="bg-white rounded-xl border border-gray-200 p-5 cursor-pointer hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="text-xs text-gray-400 font-mono">{contract.contract_number}</p>
                    <h3 className="text-lg font-bold text-gray-900">{contract.title}</h3>
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${contract.status === 'active' ? 'bg-green-100 text-green-800' : contract.status === 'draft' ? 'bg-gray-100 text-gray-800' : contract.status === 'completed' ? 'bg-blue-100 text-blue-800' : 'bg-yellow-100 text-yellow-800'}`}>{contract.status}</span>
                </div>
                <p className="text-sm text-gray-500 mb-2">{contract.counterparty}</p>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-blue-600">{`$${value.toLocaleString()}`}</span>
                  <span className="text-xs text-gray-400">{contract.contract_type}</span>
                </div>
              </div>
            );
          })}
          {contracts.length === 0 && <p className="text-center text-gray-400 py-8 col-span-3">{t.contractsPage.noContracts}</p>}
        </div>
      </div>
    );
  }

  const value = parseFloat(selectedContract.contract_value || '0');

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => setSelectedContract(null)} className="text-gray-500 hover:text-gray-700 text-sm">&larr; {t.contractsPage.backToContracts}</button>
        <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-violet-600 rounded-xl flex items-center justify-center text-white text-xl font-bold">{selectedContract.contract_number[0]?.toUpperCase()}</div>
        <div className="flex-1">
          <h2 className="text-2xl font-bold text-gray-900">{selectedContract.title}</h2>
          <p className="text-gray-500 text-sm">{selectedContract.counterparty} &middot; {selectedContract.contract_number}</p>
        </div>
        <span className={`px-3 py-1 text-sm font-medium rounded-full ${selectedContract.status === 'active' ? 'bg-green-100 text-green-800' : selectedContract.status === 'draft' ? 'bg-gray-100 text-gray-800' : 'bg-blue-100 text-blue-800'}`}>{selectedContract.status}</span>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {[
          [t.contractsPage.value, `$${value.toLocaleString()}`, '💰', 'text-blue-600'],
          [t.contractsPage.type, selectedContract.contract_type, '📋', 'text-purple-600'],
          [t.contractsPage.project, selectedContract.project_name || '—', '🏗', 'text-green-600'],
          [t.contractsPage.status, selectedContract.status, '📊', 'text-amber-600'],
        ].map(([label, val, icon, color]) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-4 text-center">
            <span className="text-xl">{icon}</span>
            <p className={`text-lg font-bold mt-1 ${color}`}>{val}</p>
            <p className="text-xs text-gray-500">{label}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
        {([
          ['overview', t.contractsPage.overview],
          ['financial', t.contractsPage.financial],
          ['timeline', t.contractsPage.timeline],
          ['documents', t.contractsPage.documents],
          ['risks', t.contractsPage.risks],
          ['ai', t.contractsPage.aiInsights],
        ] as const).map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)} className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${tab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>{label}</button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.contractsPage.contractDetails}</h3>
            <div className="space-y-2">
              {([[
                t.contractsPage.number, selectedContract.contract_number],
                [t.contractsPage.titleField, selectedContract.title],
                [t.contractsPage.counterpartyField, selectedContract.counterparty],
                [t.contractsPage.type, selectedContract.contract_type],
                [t.contractsPage.project, selectedContract.project_name || '—'],
                [t.contractsPage.value, `$${value.toLocaleString()}`],
                [t.contractsPage.signed, selectedContract.signed_date || '—'],
                [t.contractsPage.completion, selectedContract.completion_date || '—']
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between py-2 border-b border-gray-100"><span className="text-sm text-gray-500">{k}</span><span className="text-sm font-medium">{v}</span></div>
              )))}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.contractsPage.contractHealth}</h3>
            <div className="space-y-3">
              <div className="p-4 bg-green-50 rounded-lg"><p className="text-sm font-medium text-green-900">{t.contractsPage.statusLabel}: {selectedContract.status}</p><p className="text-xs text-green-700 mt-1">{t.contractsPage.contractInGoodStanding}</p></div>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-gray-50 rounded-lg"><p className="text-xs text-gray-500">{t.contractsPage.daysActive}</p><p className="text-lg font-bold text-gray-900">{selectedContract.signed_date ? Math.floor((Date.now() - new Date(selectedContract.signed_date).getTime()) / 86400000) : '—'}</p></div>
                <div className="p-3 bg-gray-50 rounded-lg"><p className="text-xs text-gray-500">{t.contractsPage.daysToCompletion}</p><p className="text-lg font-bold text-gray-900">{selectedContract.completion_date ? Math.ceil((new Date(selectedContract.completion_date).getTime() - Date.now()) / 86400000) : '—'}</p></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === 'financial' && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.contractsPage.financialSummary}</h3>
          <div className="grid grid-cols-3 gap-4">
            {[
              [t.contractsPage.contractValue, `$${value.toLocaleString()}`, 'text-blue-600'],
              [t.contractsPage.invoiced, `$${(value * 0.6).toFixed(0)}`, 'text-green-600'],
              [t.contractsPage.remaining, `$${(value * 0.4).toFixed(0)}`, 'text-amber-600'],
            ].map(([k, v, c]) => (
              <div key={k} className="p-4 bg-gray-50 rounded-xl text-center"><p className="text-xs text-gray-500">{k}</p><p className={`text-xl font-bold mt-1 ${c}`}>{v}</p></div>
            ))}
          </div>
        </div>
      )}

      {tab === 'timeline' && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.contractsPage.contractTimeline}</h3>
          <div className="space-y-3">
            {[
              { title: t.contractsPage.contractCreated, date: selectedContract.created_at, icon: '📝', color: 'bg-blue-100 text-blue-600' },
              { title: t.contractsPage.contractSigned, date: selectedContract.signed_date, icon: '✍️', color: 'bg-green-100 text-green-600' },
              { title: t.contractsPage.expectedCompletion, date: selectedContract.completion_date, icon: '🏁', color: 'bg-purple-100 text-purple-600' },
            ].map((item, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className={`w-8 h-8 ${item.color} rounded-full flex items-center justify-center text-sm shrink-0`}>{item.icon}</div>
                <div className="flex-1 pb-3 border-b border-gray-100 last:border-0">
                  <p className="text-sm font-medium text-gray-900">{item.title}</p>
                  {item.date && <p className="text-xs text-gray-500">{new Date(item.date).toLocaleDateString()}</p>}
                  {!item.date && <p className="text-xs text-gray-400">{t.contractsPage.notYet}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'documents' && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <p className="text-4xl mb-3">📄</p>
          <p className="text-gray-500 font-medium">{t.contractsPage.contractDocuments}</p>
          <p className="text-sm text-gray-400 mt-1">{t.contractsPage.documentsSubtitle}</p>
          <button className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">{t.contractsPage.uploadDocument}</button>
        </div>
      )}

      {tab === 'risks' && (
        <div className="space-y-4">
          {[
            { title: t.contractsPage.contractExpiry, level: selectedContract.completion_date && new Date(selectedContract.completion_date) < new Date(Date.now() + 30 * 86400000) ? 'high' : 'low', detail: selectedContract.completion_date ? `${t.contractsPage.expiresLabel}: ${new Date(selectedContract.completion_date).toLocaleDateString()}` : t.contractsPage.noExpirySet, action: t.contractsPage.monitorContractStatus },
            { title: t.contractsPage.valueExposure, level: value > 1000000 ? 'medium' : 'low', detail: `$${(value / 1000000).toFixed(1)}M ${t.contractsPage.contractValueLabel}`, action: t.contractsPage.reviewFinancialExposure },
          ].map(risk => (
            <div key={risk.title} className={`rounded-xl border p-4 ${risk.level === 'high' ? 'border-red-200 bg-red-50' : risk.level === 'medium' ? 'border-yellow-200 bg-yellow-50' : 'border-gray-200 bg-white'}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className={`w-3 h-3 rounded-full ${risk.level === 'high' ? 'bg-red-500' : risk.level === 'medium' ? 'bg-yellow-500' : 'bg-green-500'}`} />
                  <div><p className="text-sm font-semibold text-gray-900">{risk.title}</p><p className="text-xs text-gray-500">{risk.detail}</p></div>
                </div>
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${risk.level === 'high' ? 'bg-red-100 text-red-800' : risk.level === 'medium' ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}`}>{risk.level}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'ai' && (
        <div className="space-y-4">
          <div className="bg-gradient-to-r from-purple-600 to-violet-700 rounded-2xl p-6 text-white">
            <h3 className="font-bold text-lg mb-2">{t.contractsPage.aiContractAnalyst}</h3>
            <p className="text-purple-100 text-sm mb-4">{t.contractsPage.aiContractDesc}</p>
            <div className="flex gap-3">
              <input type="text" value={aiQuery} onChange={e => setAiQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleAskAboutContract()} placeholder={t.contractsPage.aiPlaceholder} className="flex-1 px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-purple-200 focus:outline-none" />
              <button onClick={handleAskAboutContract} className="px-6 py-3 bg-white text-purple-700 font-semibold rounded-xl hover:bg-purple-50">{t.contractsPage.ask}</button>
            </div>
          </div>
          {aiResponse && <div className="bg-white rounded-xl border border-gray-200 p-5"><p className="text-sm text-gray-700 leading-relaxed">{aiResponse}</p></div>}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[t.contractsPage.riskAssessment, t.contractsPage.financialAnalysis, t.contractsPage.timelineReview, t.contractsPage.complianceCheck].map(q => (
              <button key={q} onClick={() => setAiQuery(q)} className="p-3 bg-white border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50 text-left">{q}</button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
