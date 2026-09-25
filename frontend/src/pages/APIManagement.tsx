import React from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';
import StatusBadge from '../components/StatusBadge';

export default function APIManagement() {
  const { isRTL: _isRTL, t } = useI18n();
  const apiKeys = [
    { id: 'key_001', name: 'Production API', tenant: 'Acme Corp', requests: '1.2M', rateLimit: '1000/min', status: 'active', created: '2025-01-15' },
    { id: 'key_002', name: 'Staging API', tenant: 'GlobalTech', requests: '450K', rateLimit: '500/min', status: 'active', created: '2025-06-20' },
    { id: 'key_003', name: 'Dev API', tenant: 'StartUpXYZ', requests: '12K', rateLimit: '100/min', status: 'revoked', created: '2026-01-10' },
  ];

  return (
    <AdminPage title={t.apiManagement.title} subtitle={t.apiManagement.subtitle}>
      <div className="flex justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-2">
            <p className="text-xs text-green-700">{t.apiManagement.totalRequests}</p>
            <p className="text-lg font-bold text-green-900">2.4M</p>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2">
            <p className="text-xs text-blue-700">{t.apiManagement.activeKeys}</p>
            <p className="text-lg font-bold text-blue-900">14</p>
          </div>
        </div>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm">+ {t.apiManagement.createApiKey}</button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50"><tr>
            <th className="text-left p-3">{t.apiManagement.key}</th><th className="text-left p-3">{t.apiManagement.name}</th><th className="text-left p-3">{t.apiManagement.tenant}</th><th className="text-left p-3">{t.apiManagement.requests}</th>
            <th className="text-left p-3">{t.apiManagement.rateLimit}</th><th className="text-left p-3">Status</th><th className="text-left p-3">Created</th><th className="text-left p-3">Actions</th>
          </tr></thead>
          <tbody>
            {apiKeys.map((key, i) => (
              <tr key={i} className="border-t border-gray-100">
                <td className="p-3 font-mono text-xs">{key.id}</td>
                <td className="p-3 font-medium">{key.name}</td>
                <td className="p-3">{key.tenant}</td>
                <td className="p-3">{key.requests}</td>
                <td className="p-3">{key.rateLimit}</td>
                <td className="p-3"><StatusBadge status={key.status} /></td>
                <td className="p-3">{key.created}</td>
                <td className="p-3"><div className="flex gap-1"><button className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded">{t.apiManagement.rotate}</button><button className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded">{t.apiManagement.revoke}</button></div></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AdminPage>
  );
}
