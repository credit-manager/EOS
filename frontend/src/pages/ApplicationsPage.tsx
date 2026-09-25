import React from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';

export default function ApplicationsPage() {
  const { isRTL: _isRTL, t } = useI18n();
  return (
    <AdminPage title={t.applications.title} subtitle={t.applications.subtitle}>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[
          { name: 'ERP', status: 'active', tenants: 2847, icon: '🏗' },
          { name: 'Industry OS', status: 'active', tenants: 1500, icon: '🌍' },
          { name: 'AI Workforce', status: 'active', tenants: 1200, icon: '🤖' },
          { name: 'Analytics', status: 'active', tenants: 2000, icon: '📊' },
          { name: 'Documents', status: 'active', tenants: 2847, icon: '📄' },
          { name: 'Marketplace', status: 'active', tenants: 800, icon: '🏪' },
        ].map((app, i) => (
          <div key={i} className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-3"><span className="text-3xl">{app.icon}</span><div><h3 className="font-semibold text-gray-900">{app.name}</h3><p className="text-xs text-gray-500">{app.tenants.toLocaleString()} {t.applications.tenants}</p></div></div>
            <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">{app.status}</span>
          </div>
        ))}
      </div>
    </AdminPage>
  );
}
