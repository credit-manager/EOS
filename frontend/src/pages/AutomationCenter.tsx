import React from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';
import StatusBadge from '../components/StatusBadge';

export default function AutomationCenter() {
  const { isRTL: _isRTL, t } = useI18n();
  const automations = [
    { name: 'Invoice Approval', tenant: 'Acme Corp', trigger: 'on_create', status: 'running', executions: 1245, successRate: '98%', lastRun: '5 min ago' },
    { name: 'Onboarding Flow', tenant: 'GlobalTech', trigger: 'on_user_add', status: 'running', executions: 890, successRate: '95%', lastRun: '12 min ago' },
    { name: 'Payment Reminder', tenant: 'StartUpXYZ', trigger: 'on_schedule', status: 'paused', executions: 3420, successRate: '92%', lastRun: '1 day ago' },
  ];

  return (
    <AdminPage title={t.automationCenter.title} subtitle={t.automationCenter.subtitle}>
      <div className="flex justify-between mb-6">
        <div className="flex gap-2">
          {[
            { label: 'All', count: 47 }, { label: t.automationCenter.running, count: 32 },
            { label: t.automationCenter.paused, count: 12 }, { label: t.automationCenter.failed, count: 3 }
          ].map((tab) => (
            <button key={tab.label} className="px-3 py-1.5 rounded-lg text-sm bg-gray-100 text-gray-600 hover:bg-gray-200">{tab.label} ({tab.count})</button>
          ))}
        </div>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm">+ {t.automationCenter.newAutomation}</button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50"><tr>
            <th className="text-left p-3">{t.automationCenter.name}</th><th className="text-left p-3">{t.automationCenter.tenant}</th><th className="text-left p-3">{t.automationCenter.trigger}</th><th className="text-left p-3">Status</th>
            <th className="text-left p-3">{t.automationCenter.executions}</th><th className="text-left p-3">{t.automationCenter.successRate}</th><th className="text-left p-3">{t.automationCenter.lastRun}</th><th className="text-left p-3">Actions</th>
          </tr></thead>
          <tbody>
            {automations.map((a, i) => (
              <tr key={i} className="border-t border-gray-100">
                <td className="p-3 font-medium">{a.name}</td>
                <td className="p-3">{a.tenant}</td>
                <td className="p-3"><code className="px-1.5 py-0.5 bg-gray-100 rounded text-xs">{a.trigger}</code></td>
                <td className="p-3"><StatusBadge status={a.status} /></td>
                <td className="p-3">{a.executions.toLocaleString()}</td>
                <td className="p-3">{a.successRate}</td>
                <td className="p-3">{a.lastRun}</td>
                <td className="p-3"><div className="flex gap-1"><button className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded">Enable</button><button className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded">Edit</button><button className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded">Test</button></div></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AdminPage>
  );
}
