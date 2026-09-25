import React from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';
import StatusBadge from '../components/StatusBadge';

export default function SupportCenterPage() {
  const { isRTL: _isRTL, t } = useI18n();
  const tickets = [
    { id: 'TKT-001', tenant: 'Acme Corp', priority: 'high', status: 'open', subject: 'Login issues', assigned: 'Support Team A', created: '2 min ago' },
    { id: 'TKT-002', tenant: 'GlobalTech', priority: 'medium', status: 'in_progress', subject: 'API timeout', assigned: 'Support Team B', created: '1 hr ago' },
    { id: 'TKT-003', tenant: 'StartUpXYZ', priority: 'low', status: 'resolved', subject: 'Feature request', assigned: 'Support Team C', created: '3 days ago' },
  ];

  return (
    <AdminPage title={t.supportCenter.title} subtitle={t.supportCenter.subtitle}>
      <div className="flex justify-between mb-6">
        <div className="flex gap-2">
          {[
            { label: 'All', count: 47 }, { label: t.supportCenter.open, count: 12 },
            { label: t.supportCenter.inProgress, count: 8 }, { label: t.supportCenter.resolved, count: 27 }
          ].map((tab) => (
            <button key={tab.label} className="px-3 py-1.5 rounded-lg text-sm bg-gray-100 text-gray-600 hover:bg-gray-200">{tab.label} ({tab.count})</button>
          ))}
        </div>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm">+ {t.supportCenter.newTicket}</button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50"><tr><th className="text-left p-3">{t.supportCenter.ticket}</th><th className="text-left p-3">{t.supportCenter.tenant}</th><th className="text-left p-3">{t.supportCenter.priority}</th><th className="text-left p-3">Status</th><th className="text-left p-3">{t.supportCenter.assigned}</th><th className="text-left p-3">{t.supportCenter.created}</th></tr></thead>
          <tbody>
            {tickets.map((t, i) => (
              <tr key={i} className="border-t border-gray-100">
                <td className="p-3 font-medium">{t.id} — {t.subject}</td>
                <td className="p-3">{t.tenant}</td>
                <td className="p-3"><span className={`px-2 py-0.5 rounded text-xs ${t.priority === 'high' ? 'bg-red-100 text-red-700' : t.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'}`}>{t.priority}</span></td>
                <td className="p-3"><StatusBadge status={t.status === 'open' ? 'pending' : t.status === 'in_progress' ? 'running' : 'operational'} /></td>
                <td className="p-3">{t.assigned}</td>
                <td className="p-3">{t.created}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AdminPage>
  );
}
