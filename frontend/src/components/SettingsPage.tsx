import { useState, useEffect, useCallback } from 'react';
import { api } from '../api';
import { useI18n } from '../i18n';

interface TenantSettings {
  company_name: string;
  timezone: string;
  date_format: string;
  currency: string;
  fiscal_year_start: string;
  tax_id: string;
  address: string;
  phone: string;
  email: string;
  website: string;
  logo_url: string;
}

interface NotificationPrefs {
  email_enabled: boolean;
  push_enabled: boolean;
  sms_enabled: boolean;
  weekly_report: boolean;
  project_updates: boolean;
  approval_requests: boolean;
  budget_alerts: boolean;
  payment_notifications: boolean;
}

type Tab = 'general' | 'appearance' | 'notifications' | 'security' | 'integrations' | 'billing';

export default function SettingsPage({ token }: { token: string }) {
  const { language, setLanguage, t } = useI18n();
  const [activeTab, setActiveTab] = useState<Tab>('general');
  const [formData, setFormData] = useState<TenantSettings>({
    company_name: '', timezone: 'Asia/Riyadh', date_format: 'YYYY-MM-DD', currency: 'SAR',
    fiscal_year_start: '01', tax_id: '', address: '', phone: '', email: '', website: '', logo_url: '',
  });
  const [notifications, setNotifications] = useState<NotificationPrefs>({
    email_enabled: true, push_enabled: true, sms_enabled: false, weekly_report: true,
    project_updates: true, approval_requests: true, budget_alerts: true, payment_notifications: true,
  });
  const [passwordData, setPasswordData] = useState({ current: '', new: '', confirm: '' });
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api<{
        company_name: string; timezone: string; date_format: string; currency: string;
        fiscal_year_start: string; tax_id: string; address: string; phone: string;
        email: string; website: string; logo_url: string; notifications: Record<string, boolean>;
      }>('/settings', token);
      setFormData({
        company_name: data.company_name || '', timezone: data.timezone || 'Asia/Riyadh',
        date_format: data.date_format || 'YYYY-MM-DD', currency: data.currency || 'SAR',
        fiscal_year_start: data.fiscal_year_start || '01', tax_id: data.tax_id || '',
        address: data.address || '', phone: data.phone || '', email: data.email || '',
        website: data.website || '', logo_url: data.logo_url || '',
      });
      if (data.notifications) {
        setNotifications(prev => ({ ...prev, ...data.notifications }));
      }
    } catch {
      // fallback to defaults
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void loadSettings(); }, [loadSettings]);

  const saveGeneral = async () => {
    setSaving(true);
    try {
      await api('/settings', token, { method: 'PATCH', body: JSON.stringify(formData) });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      alert(err instanceof Error ? err.message : t.settingsPage.failedToSave);
    } finally {
      setSaving(false);
    }
  };

  const saveNotifications = async () => {
    setSaving(true);
    try {
      await api('/settings', token, { method: 'PATCH', body: JSON.stringify({ notifications }) });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      alert(err instanceof Error ? err.message : t.settingsPage.failedToSave);
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = (e: React.FormEvent) => {
    e.preventDefault();
    if (passwordData.new !== passwordData.confirm) { alert(t.settingsPage.passwordsDoNotMatch); return; }
    alert(t.settingsPage.passwordComingSoon);
  };

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: 'general', label: t.settingsPage.tabGeneral, icon: '🏢' },
    { id: 'appearance', label: t.settingsPage.tabAppearance, icon: '🎨' },
    { id: 'notifications', label: t.settingsPage.tabNotifications, icon: '🔔' },
    { id: 'security', label: t.settingsPage.tabSecurity, icon: '🔒' },
    { id: 'integrations', label: t.settingsPage.tabIntegrations, icon: '🔗' },
    { id: 'billing', label: t.settingsPage.tabBilling, icon: '💳' },
  ];

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">{t.settingsPage.title}</h1>
        {saved && <span className="px-3 py-1 bg-green-100 text-green-700 text-sm font-medium rounded-full">{t.settingsPage.saved}</span>}
      </div>

      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${activeTab === tab.id ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'general' && (
        <div className="space-y-6 max-w-3xl">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">{t.settingsPage.companyInformation}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {([
                [t.settingsPage.companyName, 'company_name', 'text'],
                [t.settingsPage.taxId, 'tax_id', 'text'],
                [t.settingsPage.phone, 'phone', 'tel'],
                [t.settingsPage.email, 'email', 'email'],
                [t.settingsPage.website, 'website', 'url'],
                [t.settingsPage.address, 'address', 'text'],
              ] as const).map(([label, field, type]) => (
                <div key={field}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                  <input type={type} value={formData[field] || ''} onChange={e => setFormData({ ...formData, [field]: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" />
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">{t.settingsPage.regionalSettings}</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t.settingsPage.timezone}</label>
                <select value={formData.timezone} onChange={e => setFormData({ ...formData, timezone: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500">
                  <option value="Asia/Riyadh">Asia/Riyadh (GMT+3)</option>
                  <option value="Asia/Dubai">Asia/Dubai (GMT+4)</option>
                  <option value="Africa/Cairo">Africa/Cairo (GMT+2)</option>
                  <option value="UTC">UTC (GMT+0)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t.settingsPage.dateFormat}</label>
                <select value={formData.date_format} onChange={e => setFormData({ ...formData, date_format: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500">
                  <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                  <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                  <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t.settingsPage.currency}</label>
                <select value={formData.currency} onChange={e => setFormData({ ...formData, currency: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500">
                  <option value="SAR">SAR - Saudi Riyal</option>
                  <option value="USD">USD - US Dollar</option>
                  <option value="EUR">EUR - Euro</option>
                  <option value="AED">AED - UAE Dirham</option>
                  <option value="EGP">EGP - Egyptian Pound</option>
                </select>
              </div>
            </div>
          </div>
          <button onClick={saveGeneral} disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">{saving ? t.settingsPage.saving : t.settingsPage.saveChanges}</button>
        </div>
      )}

      {activeTab === 'appearance' && (
        <div className="space-y-6 max-w-3xl">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">{t.settingsPage.language}</h3>
            <div className="grid grid-cols-2 gap-3">
              {(['en', 'ar'] as const).map(lang => (
                <button key={lang} onClick={() => setLanguage(lang)} className={`p-4 border-2 rounded-xl text-left transition-all ${language === lang ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}>
                  <p className="font-semibold text-gray-900">{lang === 'en' ? 'English' : 'العربية'}</p>
                  <p className="text-xs text-gray-500 mt-1">{lang === 'en' ? t.settingsPage.leftToRight : t.settingsPage.rightToLeft}</p>
                </button>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">{t.settingsPage.theme}</h3>
            <div className="grid grid-cols-3 gap-3">
              {(['light', 'dark', 'system'] as const).map(theme => (
                <button key={theme} className={`p-4 border-2 rounded-xl text-center transition-all ${theme === 'light' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}>
                  <span className="text-2xl">{theme === 'light' ? '☀️' : theme === 'dark' ? '🌙' : '💻'}</span>
                  <p className="text-sm font-medium text-gray-900 mt-2">{theme === 'light' ? t.settingsPage.light : theme === 'dark' ? t.settingsPage.dark : t.settingsPage.systemTheme}</p>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'notifications' && (
        <div className="space-y-6 max-w-3xl">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">{t.settingsPage.notificationChannels}</h3>
            <div className="space-y-3">
              {([
                [t.settingsPage.emailNotifications, 'email_enabled', t.settingsPage.emailNotificationsDesc],
                [t.settingsPage.pushNotifications, 'push_enabled', t.settingsPage.pushNotificationsDesc],
                [t.settingsPage.smsNotifications, 'sms_enabled', t.settingsPage.smsNotificationsDesc],
              ] as const).map(([label, field, desc]) => (
                <label key={field} className="flex items-center justify-between p-4 border border-gray-200 rounded-xl hover:bg-gray-50 cursor-pointer">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{label}</p>
                    <p className="text-xs text-gray-500">{desc}</p>
                  </div>
                  <div className="relative">
                    <input type="checkbox" checked={notifications[field]} onChange={e => setNotifications({ ...notifications, [field]: e.target.checked })} className="sr-only" />
                    <div className={`w-11 h-6 rounded-full transition-colors ${notifications[field] ? 'bg-blue-600' : 'bg-gray-300'}`} />
                    <div className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${notifications[field] ? 'translate-x-5' : ''}`} />
                  </div>
                </label>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">{t.settingsPage.notificationCategories}</h3>
            <div className="space-y-3">
              {([
                [t.settingsPage.weeklyReports, 'weekly_report', '📊'],
                [t.settingsPage.projectUpdates, 'project_updates', '🏗'],
                [t.settingsPage.approvalRequests, 'approval_requests', '⏳'],
                [t.settingsPage.budgetAlerts, 'budget_alerts', '💰'],
                [t.settingsPage.paymentNotifications, 'payment_notifications', '💳'],
              ] as const).map(([label, field, icon]) => (
                <label key={field} className="flex items-center justify-between p-4 border border-gray-200 rounded-xl hover:bg-gray-50 cursor-pointer">
                  <div className="flex items-center gap-3">
                    <span className="text-lg">{icon}</span>
                    <p className="text-sm font-medium text-gray-900">{label}</p>
                  </div>
                  <div className="relative">
                    <input type="checkbox" checked={notifications[field]} onChange={e => setNotifications({ ...notifications, [field]: e.target.checked })} className="sr-only" />
                    <div className={`w-11 h-6 rounded-full transition-colors ${notifications[field] ? 'bg-blue-600' : 'bg-gray-300'}`} />
                    <div className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${notifications[field] ? 'translate-x-5' : ''}`} />
                  </div>
                </label>
              ))}
            </div>
          </div>
          <button onClick={saveNotifications} disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">{saving ? t.settingsPage.saving : t.settingsPage.saveChanges}</button>
        </div>
      )}

      {activeTab === 'security' && (
        <div className="space-y-6 max-w-3xl">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">{t.settingsPage.changePassword}</h3>
            <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t.settingsPage.currentPassword}</label>
                <input type="password" value={passwordData.current} onChange={e => setPasswordData({ ...passwordData, current: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" required />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t.settingsPage.newPassword}</label>
                <input type="password" value={passwordData.new} onChange={e => setPasswordData({ ...passwordData, new: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" required minLength={8} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t.settingsPage.confirmPassword}</label>
                <input type="password" value={passwordData.confirm} onChange={e => setPasswordData({ ...passwordData, confirm: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" required />
              </div>
              <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">{t.settingsPage.changePassword}</button>
            </form>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">{t.settingsPage.twoFactorAuth}</h3>
            <div className="flex items-center justify-between p-4 border border-gray-200 rounded-xl">
              <div>
                <p className="text-sm font-medium text-gray-900">{t.settingsPage.twoFAViaApp}</p>
                <p className="text-xs text-gray-500">{t.settingsPage.useAuthenticatorApp}</p>
              </div>
              <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">{t.settingsPage.enable}</button>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">{t.settingsPage.activeSessions}</h3>
            <div className="p-4 bg-gray-50 rounded-xl">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">{t.settingsPage.currentSession}</p>
                  <p className="text-xs text-gray-500">{t.settingsPage.lastActiveJustNow}</p>
                </div>
                <span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded-full">{t.settingsPage.active}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'integrations' && (
        <div className="space-y-6 max-w-3xl">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">{t.settingsPage.connectedServices}</h3>
            <div className="space-y-3">
              {([
                [t.settingsPage.emailSMTP, t.settingsPage.emailSMTPDesc, '📧', false],
                [t.settingsPage.smsGateway, t.settingsPage.smsGatewayDesc, '📱', false],
                [t.settingsPage.paymentGateway, t.settingsPage.paymentGatewayDesc, '💳', false],
                [t.settingsPage.cloudStorage, t.settingsPage.cloudStorageDesc, '☁️', false],
                [t.settingsPage.accountingSoftware, t.settingsPage.accountingSoftwareDesc, '📊', false],
              ] as [string, string, string, boolean][]).map(([name, desc, icon, connected]) => (
                <div key={name} className="flex items-center justify-between p-4 border border-gray-200 rounded-xl">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{icon}</span>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{name}</p>
                      <p className="text-xs text-gray-500">{desc}</p>
                    </div>
                  </div>
                  <button className={`px-4 py-2 rounded-lg text-sm font-medium ${connected ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700 hover:bg-blue-200'}`}>{connected ? t.settingsPage.connected : t.settingsPage.connect}</button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'billing' && (
        <div className="space-y-6 max-w-3xl">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">{t.settingsPage.currentPlan}</h3>
            <div className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-lg font-bold text-blue-900">{t.settingsPage.professionalPlan}</p>
                  <p className="text-sm text-blue-700">{t.settingsPage.planDescription}</p>
                </div>
                <p className="text-2xl font-bold text-blue-900">$499<span className="text-sm font-normal">/mo</span></p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">{t.settingsPage.usageThisMonth}</h3>
            <div className="space-y-4">
              {([
                [t.settingsPage.users, 12, 50, '👥'],
                [t.settingsPage.aiQueries, 847, 1000, '🤖'],
                [t.settingsPage.storage, 2.4, 10, '💾'],
                [t.settingsPage.apiCalls, 15420, 50000, '🔗'],
              ] as [string, number, number, string][]).map(([label, used, limit, icon]) => (
                <div key={label}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-600">{icon} {label}</span>
                    <span className="font-medium">{used} / {limit}</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-1.5">
                    <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${Math.min((used / limit) * 100, 100)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">{t.settingsPage.paymentHistory}</h3>
            <div className="space-y-2">
              {[
                ['Sep 2026', '$499.00', 'Paid', '✅'],
                ['Aug 2026', '$499.00', 'Paid', '✅'],
                ['Jul 2026', '$499.00', 'Paid', '✅'],
              ].map(([month, amount, _status, icon]) => (
                <div key={month} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <span className="text-sm text-gray-900">{month}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium">{amount}</span>
                    <span className="text-xs text-green-600">{icon} {t.settingsPage.paid}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
