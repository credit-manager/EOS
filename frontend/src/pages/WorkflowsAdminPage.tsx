import React from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';
import StatusBadge from '../components/StatusBadge';

export default function WorkflowsAdminPage() {
  const { isRTL: _isRTL, t } = useI18n();
  return (
    <AdminPage title={t.master.automation.workflows} subtitle="Manage all platform workflows">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Workflow Templates</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { name: 'Approval', states: 4, icon: '✅' },
            { name: 'Review', states: 5, icon: '🔍' },
            { name: 'Onboarding', states: 3, icon: '🎉' },
          ].map((w, i) => (
            <div key={i} className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2 mb-2"><span className="text-xl">{w.icon}</span><span className="font-medium">{w.name}</span></div>
              <p className="text-xs text-gray-500">{w.states} states</p>
              <StatusBadge status="operational" />
            </div>
          ))}
        </div>
      </div>
    </AdminPage>
  );
}
