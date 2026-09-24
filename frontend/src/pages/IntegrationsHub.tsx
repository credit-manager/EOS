import React from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';
import StatusBadge from '../components/StatusBadge';

export default function IntegrationsHub() {
  const { isRTL: _isRTL, t } = useI18n();
  const categories = [
    { name: t.master.integrations.payment, integrations: [
      { name: 'Stripe', status: 'connected', tenants: 2847, lastSync: t.integrationsHub.lastSync + ': 2 min' },
      { name: 'PayPal', status: 'connected', tenants: 890, lastSync: t.integrationsHub.lastSync + ': 5 min' },
    ]},
    { name: t.master.integrations.email, integrations: [
      { name: 'SendGrid', status: 'connected', tenants: 2847, lastSync: t.integrationsHub.lastSync + ': 1 min' },
      { name: 'SES', status: 'warning', tenants: 120, lastSync: t.integrationsHub.lastSync + ': 1 hr' },
    ]},
    { name: t.master.integrations.sms, integrations: [
      { name: 'Twilio', status: 'connected', tenants: 1500, lastSync: t.integrationsHub.lastSync + ': 3 min' },
    ]},
    { name: t.master.integrations.aiProviders, integrations: [
      { name: 'OpenAI', status: 'connected', tenants: 2847, lastSync: t.integrationsHub.realtime },
      { name: 'Anthropic', status: 'connected', tenants: 890, lastSync: t.integrationsHub.realtime },
      { name: 'Google AI', status: 'disconnected', tenants: 0, lastSync: '-' },
    ]},
  ];

  return (
    <AdminPage title={t.integrationsHub.title} subtitle={t.integrationsHub.subtitle}>
      <div className="space-y-8">
        {categories.map((cat, i) => (
          <div key={i}>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">{cat.name}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {cat.integrations.map((int, j) => (
                <div key={j} className="bg-white rounded-xl border border-gray-200 p-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">{int.name}</p>
                    <p className="text-xs text-gray-500">{int.tenants.toLocaleString()} {t.integrationsHub.tenants} · {int.lastSync}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={int.status === 'connected' ? 'operational' : int.status === 'warning' ? 'warning' : 'offline'} />
                    <button className="px-3 py-1 bg-blue-600 text-white rounded-lg text-xs">{t.integrationsHub.configure}</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </AdminPage>
  );
}
