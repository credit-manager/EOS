import { useState, useEffect } from 'react';
import { useI18n } from '../i18n';

interface Integration {
  id: string;
  code: string;
  name: string;
  description?: string;
  integration_type: string;
  provider?: string;
  status: string;
  is_active: boolean;
  timeout_seconds: number;
  retry_count: number;
  created_at: string;
}

interface IntegrationLog {
  id: string;
  integration_id: string;
  endpoint_name?: string;
  direction: string;
  status: string;
  request_method?: string;
  request_url?: string;
  response_status?: number;
  duration_ms?: number;
  created_at: string;
}

export default function IntegrationsPage({ token }: { token: string }) {
  const { t } = useI18n();
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [logs, setLogs] = useState<IntegrationLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'list' | 'logs'>('list');
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ code: '', name: '', integration_type: 'rest', description: '' });

  useEffect(() => {
    Promise.all([
      fetch('/api/v1/integrations', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      fetch('/api/v1/integrations/logs', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
    ]).then(([ints, lgs]) => {
      setIntegrations(ints);
      setLogs(lgs);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [token]);

  const handleCreate = async () => {
    const r = await fetch('/api/v1/integrations', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    if (r.ok) {
      const created = await r.json();
      setIntegrations(prev => [...prev, created]);
      setShowCreate(false);
      setForm({ code: '', name: '', integration_type: 'rest', description: '' });
    }
  };

  const statusColor = (s: string) => s === 'active' ? 'bg-green-100 text-green-700' : s === 'error' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600';
  const logStatusColor = (s: string) => s === 'success' ? 'bg-green-100 text-green-700' : s === 'failed' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700';

  if (loading) return <div className="flex items-center justify-center h-64"><p className="text-gray-500">{t.integrationsPage.loading}</p></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">{t.integrationsPage.title}</h2>
        <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">{t.integrationsPage.newIntegration}</button>
      </div>

      <div className="flex gap-2 border-b border-gray-200">
        {(['list', 'logs'] as const).map(tabItem => (
          <button key={tabItem} onClick={() => setTab(tabItem)} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === tabItem ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {tabItem === 'list' ? `${t.integrationsPage.tabIntegrations} (${integrations.length})` : `${t.integrationsPage.tabLogs} (${logs.length})`}
          </button>
        ))}
      </div>

      {tab === 'list' && (
        <div className="grid gap-4">
          {integrations.map(int => (
            <div key={int.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center text-lg">🔗</div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{int.name}</h3>
                    <p className="text-sm text-gray-500">{int.code} &middot; {int.integration_type}</p>
                  </div>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColor(int.status)}`}>{int.status}</span>
              </div>
              {int.description && <p className="mt-2 text-sm text-gray-600">{int.description}</p>}
              <div className="mt-3 flex gap-4 text-xs text-gray-400">
                <span>{t.integrationsPage.timeout} {int.timeout_seconds}s</span>
                <span>{t.integrationsPage.retries} {int.retry_count}</span>
                <span>{t.integrationsPage.provider} {int.provider || t.integrationsPage.na}</span>
              </div>
            </div>
          ))}
          {integrations.length === 0 && <p className="text-center text-gray-400 py-8">No integrations configured</p>}
        </div>
      )}

      {tab === 'logs' && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Endpoint</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Direction</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Method</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {logs.map(log => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{log.endpoint_name || '-'}</td>
                  <td className="px-4 py-3 text-sm"><span className={`px-2 py-0.5 rounded text-xs ${log.direction === 'outbound' ? 'bg-blue-50 text-blue-600' : 'bg-green-50 text-green-600'}`}>{log.direction}</span></td>
                  <td className="px-4 py-3 text-sm text-gray-600">{log.request_method || '-'}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-1 rounded-full text-xs font-medium ${logStatusColor(log.status)}`}>{log.status}</span></td>
                  <td className="px-4 py-3 text-sm text-gray-500">{log.duration_ms ? `${log.duration_ms.toFixed(0)}ms` : '-'}</td>
                  <td className="px-4 py-3 text-xs text-gray-400">{new Date(log.created_at).toLocaleString()}</td>
                </tr>
              ))}
              {logs.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No logs yet</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowCreate(false)}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-bold mb-4">New Integration</h3>
            <div className="space-y-3">
              <input placeholder="Code" value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))} className="w-full px-4 py-2 border rounded-lg" />
              <input placeholder="Name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className="w-full px-4 py-2 border rounded-lg" />
              <select value={form.integration_type} onChange={e => setForm(f => ({ ...f, integration_type: e.target.value }))} className="w-full px-4 py-2 border rounded-lg">
                <option value="rest">REST API</option>
                <option value="graphql">GraphQL</option>
                <option value="webhook">Webhook</option>
                <option value="soap">SOAP</option>
              </select>
              <textarea placeholder="Description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} className="w-full px-4 py-2 border rounded-lg" rows={2} />
              <div className="flex gap-3 justify-end">
                <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-gray-600 hover:text-gray-800">Cancel</button>
                <button onClick={handleCreate} disabled={!form.code || !form.name} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">Create</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
