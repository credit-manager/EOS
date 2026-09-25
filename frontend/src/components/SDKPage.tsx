import { useState, useEffect } from 'react';
import { useI18n } from '../i18n';

interface SDKApp { id: string; code: string; name: string; app_type: string; version: string; is_installed: boolean; created_at: string; }
interface APIKey { id: string; name: string; key_prefix: string; scopes?: string[]; is_active: boolean; use_count: number; created_at: string; }
interface Webhook { id: string; code: string; name: string; event_type: string; url: string; is_active: boolean; trigger_count: number; }
interface EventStat { total: number; pending: number; processed: number; failed: number; }

export default function SDKPage({ token }: { token: string }) {
  const { t } = useI18n();
  const [tab, setTab] = useState<'apps' | 'keys' | 'webhooks' | 'events'>('apps');
  const [apps, setApps] = useState<SDKApp[]>([]);
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [eventStats, setEventStats] = useState<EventStat | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreateApp, setShowCreateApp] = useState(false);
  const [showCreateKey, setShowCreateKey] = useState(false);
  const [form, setForm] = useState({ code: '', name: '', app_type: 'plugin' });
  const [keyName, setKeyName] = useState('');

  useEffect(() => {
    Promise.all([
      fetch('/api/v1/sdk/apps', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      fetch('/api/v1/sdk/api-keys', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      fetch('/api/v1/sdk/webhooks', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      fetch('/api/v1/sdk/events/stats', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
    ]).then(([a, k, w, e]) => {
      setApps(a); setKeys(k); setWebhooks(w); setEventStats(e);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [token]);

  const handleCreateApp = async () => {
    const r = await fetch('/api/v1/sdk/apps', {
      method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    if (r.ok) {
      const created = await r.json();
      setApps(prev => [...prev, created]);
      setShowCreateApp(false);
      setForm({ code: '', name: '', app_type: 'plugin' });
    }
  };

  const handleCreateKey = async () => {
    const r = await fetch('/api/v1/sdk/api-keys', {
      method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: keyName }),
    });
    if (r.ok) {
      const result = await r.json();
      setKeys(prev => [...prev, result]);
      setShowCreateKey(false);
      setKeyName('');
      alert(`${t.sdkPage.keyCreated}: ${result.key}\n\n${t.sdkPage.keyCreatedHint}`);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><p className="text-gray-500">{t.sdkPage.loading}</p></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{t.sdkPage.title}</h2>
          <p className="text-sm text-gray-500">{t.sdkPage.subtitle}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowCreateApp(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">+ {t.sdkPage.newApp}</button>
          <button onClick={() => setShowCreateKey(true)} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">+ {t.sdkPage.apiKey}</button>
        </div>
      </div>

      {eventStats && (
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: t.sdkPage.totalEvents, value: eventStats.total, color: 'bg-blue-50 text-blue-700' },
            { label: t.sdkPage.pending, value: eventStats.pending, color: 'bg-yellow-50 text-yellow-700' },
            { label: t.sdkPage.processed, value: eventStats.processed, color: 'bg-green-50 text-green-700' },
            { label: t.sdkPage.failed, value: eventStats.failed, color: 'bg-red-50 text-red-700' },
          ].map(s => (
            <div key={s.label} className={`rounded-lg p-4 ${s.color}`}>
              <p className="text-2xl font-bold">{s.value}</p>
              <p className="text-sm opacity-75">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2 border-b border-gray-200">
        {(['apps', 'keys', 'webhooks', 'events'] as const).map(tabId => (
          <button key={tabId} onClick={() => setTab(tabId)} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === tabId ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {tabId === 'apps' ? `${t.sdkPage.apps} (${apps.length})` : tabId === 'keys' ? `${t.sdkPage.apiKeys} (${keys.length})` : tabId === 'webhooks' ? `${t.sdkPage.webhooks} (${webhooks.length})` : t.sdkPage.events}
          </button>
        ))}
      </div>

      {tab === 'apps' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {apps.map(app => (
            <div key={app.id} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 bg-cyan-100 rounded-lg flex items-center justify-center text-lg">🧑‍💻</div>
                <div>
                  <h3 className="font-semibold text-gray-900">{app.name}</h3>
                  <p className="text-xs text-gray-500 font-mono">{app.code}</p>
                </div>
              </div>
              <div className="flex gap-2 text-xs mt-2">
                <span className="px-2 py-0.5 bg-gray-100 rounded">{app.app_type}</span>
                <span className="px-2 py-0.5 bg-gray-100 rounded">v{app.version}</span>
              </div>
            </div>
          ))}
          {apps.length === 0 && <p className="text-center text-gray-400 py-8 col-span-3">{t.sdkPage.noAppsRegistered}</p>}
        </div>
      )}

      {tab === 'keys' && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b"><tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.sdkPage.name}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.sdkPage.keyPrefix}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.sdkPage.uses}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.sdkPage.status}</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-200">
              {keys.map(k => (
                <tr key={k.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{k.name}</td>
                  <td className="px-4 py-3 font-mono text-sm text-gray-600">{k.key_prefix}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{k.use_count}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-0.5 rounded text-xs ${k.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{k.is_active ? t.sdkPage.active : t.sdkPage.revoked}</span></td>
                </tr>
              ))}
              {keys.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">{t.sdkPage.noApiKeys}</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'webhooks' && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b"><tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.sdkPage.name}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.sdkPage.event}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.sdkPage.url}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.sdkPage.triggers}</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-200">
              {webhooks.map(w => (
                <tr key={w.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{w.name}</td>
                  <td className="px-4 py-3"><span className="px-2 py-0.5 bg-orange-50 text-orange-600 rounded text-xs">{w.event_type}</span></td>
                  <td className="px-4 py-3 text-sm font-mono text-gray-600 truncate max-w-[200px]">{w.url}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{w.trigger_count}</td>
                </tr>
              ))}
              {webhooks.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">{t.sdkPage.noWebhooks}</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'events' && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <p className="text-gray-500">{t.sdkPage.eventsDashboard} - {t.sdkPage.eventsDashboardDesc}</p>
        </div>
      )}

      {showCreateApp && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowCreateApp(false)}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-bold mb-4">{t.sdkPage.newSdkApp}</h3>
            <div className="space-y-3">
              <input placeholder={t.sdkPage.code} value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))} className="w-full px-4 py-2 border rounded-lg" />
              <input placeholder={t.sdkPage.name} value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className="w-full px-4 py-2 border rounded-lg" />
              <select value={form.app_type} onChange={e => setForm(f => ({ ...f, app_type: e.target.value }))} className="w-full px-4 py-2 border rounded-lg">
                <option value="plugin">{t.sdkPage.plugin}</option>
                <option value="connector">{t.sdkPage.connector}</option>
                <option value="widget">{t.sdkPage.widget}</option>
                <option value="automation">{t.sdkPage.automation}</option>
              </select>
              <div className="flex gap-3 justify-end">
                <button onClick={() => setShowCreateApp(false)} className="px-4 py-2 text-gray-600">{t.sdkPage.cancel}</button>
                <button onClick={handleCreateApp} disabled={!form.code || !form.name} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">{t.sdkPage.create}</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showCreateKey && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowCreateKey(false)}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-bold mb-4">{t.sdkPage.generateApiKey}</h3>
            <div className="space-y-3">
              <input placeholder={t.sdkPage.keyName} value={keyName} onChange={e => setKeyName(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
              <div className="flex gap-3 justify-end">
                <button onClick={() => setShowCreateKey(false)} className="px-4 py-2 text-gray-600">{t.sdkPage.cancel}</button>
                <button onClick={handleCreateKey} disabled={!keyName} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">{t.sdkPage.generateKey}</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
