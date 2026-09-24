import React from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';

export default function SystemSettingsPage() {
  const { isRTL: _isRTL, t } = useI18n();
  const tabs = [t.systemSettings.generalTab, t.systemSettings.emailTab, t.systemSettings.notificationsTab, t.systemSettings.securityTab, t.systemSettings.systemTab, t.systemSettings.aiTab];

  const sections = {
    general: [
      { label: t.systemSettings.platformName, value: '2TO EOS', type: 'text' },
      { label: t.systemSettings.defaultLanguage, value: 'English', type: 'select' },
      { label: t.systemSettings.timezone, value: 'Asia/Riyadh', type: 'select' },
      { label: t.systemSettings.defaultCurrency, value: 'SAR', type: 'select' },
    ],
    email: [
      { label: t.systemSettings.smtpHost, value: 'smtp.sendgrid.com', type: 'text' },
      { label: t.systemSettings.senderEmail, value: 'no-reply@2to-eos.com', type: 'text' },
      { label: t.systemSettings.templates, value: '5 templates', type: 'text' },
    ],
    notifications: [
      { label: t.systemSettings.emailNotifications, value: true, type: 'toggle' },
      { label: t.systemSettings.pushNotifications, value: true, type: 'toggle' },
      { label: t.systemSettings.smsAlerts, value: false, type: 'toggle' },
    ],
    security: [
      { label: t.systemSettings.sessionTimeout, value: '30 minutes', type: 'select' },
      { label: t.systemSettings.passwordMinLength, value: '12', type: 'number' },
      { label: t.systemSettings.mfaRequired, value: true, type: 'toggle' },
    ],
    system: [
      { label: t.systemSettings.maintenanceMode, value: false, type: 'toggle' },
      { label: t.systemSettings.debugMode, value: false, type: 'toggle' },
      { label: t.systemSettings.cacheDuration, value: '15 minutes', type: 'select' },
    ],
    ai: [
      { label: t.systemSettings.defaultModel, value: 'GPT-4o-mini', type: 'select' },
      { label: t.systemSettings.fallbackModel, value: 'Claude Sonnet 4', type: 'select' },
      { label: t.systemSettings.tokenLimit, value: '10000', type: 'number' },
    ],
  };

  return (
    <AdminPage title={t.systemSettings.title} subtitle={t.systemSettings.subtitle}>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            {tabs.map((tab) => (
              <button key={tab} className="w-full text-left px-3 py-2 rounded-lg text-sm capitalize {tab === t.systemSettings.generalTab ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-50'}">
                {tab}
              </button>
            ))}
          </div>
        </div>
        <div className="lg:col-span-3">
          <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
            {sections.general.map((s, i) => (
              <div key={i} className="flex items-center justify-between py-3 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">{s.label}</span>
                <span className="text-sm text-gray-900">{String(s.value)}</span>
              </div>
            ))}
            <button className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg font-medium">{t.systemSettings.saveChanges}</button>
          </div>
        </div>
      </div>
    </AdminPage>
  );
}
