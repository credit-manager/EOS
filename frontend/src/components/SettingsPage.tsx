import React, { useState, useEffect } from 'react';
import { TranslationKeys } from '../i18n';
import { useI18n } from '../i18n';

interface SettingsPageProps {
  t: TranslationKeys;
  token: string;
}

export default function SettingsPage({ t: _t, token: _token }: SettingsPageProps) {
  const { language, setLanguage, isRTL: _isRTL } = useI18n();
  const [activeTab, setActiveTab] = useState<
    'general' | 'appearance' | 'notifications' | 'security'
  >('general');
  const [formData, setFormData] = useState({
    company_name: '',
    timezone: 'Asia/Riyadh',
    date_format: 'YYYY-MM-DD',
    currency: 'SAR',
  });
  const [notifications, setNotifications] = useState({
    email: true,
    push: true,
    sms: false,
    weekly_report: true,
    project_updates: true,
  });
  const [passwordData, setPasswordData] = useState({
    current: '',
    new: '',
    confirm: '',
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    // Load settings from localStorage
    const stored = localStorage.getItem('2to-eos-settings');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setFormData(parsed.general || formData);
        setNotifications(parsed.notifications || notifications);
      } catch (e) {
        console.error('Failed to load settings:', e);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSaveGeneral = () => {
    localStorage.setItem(
      '2to-eos-settings',
      JSON.stringify({
        general: formData,
        notifications,
      })
    );
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const handleSaveNotifications = () => {
    localStorage.setItem(
      '2to-eos-settings',
      JSON.stringify({
        general: formData,
        notifications,
      })
    );
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwordData.new !== passwordData.confirm) {
      alert('Passwords do not match');
      return;
    }
    // TODO: Implement password change API
    alert('Password change feature coming soon');
  };

  const tabs = [
    { id: 'general', label: 'General', icon: '🏢' },
    { id: 'appearance', label: 'Appearance', icon: '🎨' },
    { id: 'notifications', label: 'Notifications', icon: '🔔' },
    { id: 'security', label: 'Security', icon: '🔒' },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="border-b border-gray-200">
          <nav className="flex gap-1 px-4" aria-label="Settings tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() =>
                  setActiveTab(tab.id as 'general' | 'appearance' | 'notifications' | 'security')
                }
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {saved && (
            <div className="mb-4 p-4 bg-green-50 text-green-700 rounded-lg">
              Settings saved successfully!
            </div>
          )}

          {activeTab === 'general' && (
            <div className="space-y-6 max-w-2xl">
              <h2 className="text-lg font-semibold text-gray-900">Company Information</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Company Name
                  </label>
                  <input
                    type="text"
                    value={formData.company_name}
                    onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
                  <select
                    value={formData.timezone}
                    onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="Asia/Riyadh">Asia/Riyadh (GMT+3)</option>
                    <option value="UTC">UTC (GMT+0)</option>
                    <option value="Asia/Dubai">Asia/Dubai (GMT+4)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Date Format
                  </label>
                  <select
                    value={formData.date_format}
                    onChange={(e) => setFormData({ ...formData, date_format: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                    <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                    <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Currency</label>
                  <select
                    value={formData.currency}
                    onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="SAR">SAR (Saudi Riyal)</option>
                    <option value="USD">USD (US Dollar)</option>
                    <option value="EUR">EUR (Euro)</option>
                  </select>
                </div>
              </div>
              <button onClick={handleSaveGeneral} className="btn-primary">
                Save Changes
              </button>
            </div>
          )}

          {activeTab === 'appearance' && (
            <div className="space-y-6 max-w-2xl">
              <h2 className="text-lg font-semibold text-gray-900">Appearance</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-medium font-medium text-gray-900 mb-4">Language</h3>
                  <div className="space-y-3">
                    {['en', 'ar'].map((lang) => (
                      <label
                        key={lang}
                        className="flex items-center gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50"
                      >
                        <input
                          type="radio"
                          name="language"
                          value={lang}
                          checked={language === lang}
                          onChange={() => setLanguage(lang as 'en' | 'ar')}
                          className="text-blue-600 focus:ring-blue-500"
                        />
                        <span className="font-medium">{lang === 'en' ? 'English' : 'العربية'}</span>
                        <span className="text-sm text-gray-500">
                          ({lang === 'en' ? 'LTR' : 'RTL'})
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
                <div>
                  <h3 className="text-medium font-medium text-gray-900 mb-4">Theme</h3>
                  <div className="space-y-3">
                    <label className="flex items-center gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
                      <input
                        type="radio"
                        name="theme"
                        value="light"
                        checked
                        className="text-blue-600"
                      />
                      <span className="font-medium">Light Mode</span>
                    </label>
                    <label className="flex items-center gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
                      <input type="radio" name="theme" value="dark" className="text-blue-600" />
                      <span className="font-medium">Dark Mode</span>
                    </label>
                    <label className="flex items-center gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
                      <input type="radio" name="theme" value="system" className="text-blue-600" />
                      <span className="font-medium">System Default</span>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="space-y-6 max-w-2xl">
              <h2 className="text-lg font-semibold text-gray-900">Notification Preferences</h2>
              <div className="space-y-4">
                {Object.entries(notifications).map(([key, value]) => (
                  <label
                    key={key}
                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50"
                  >
                    <span className="font-medium capitalize">{key.replace('_', ' ')}</span>
                    <input
                      type="checkbox"
                      checked={value}
                      onChange={(e) =>
                        setNotifications({ ...notifications, [key]: e.target.checked })
                      }
                      className="h-5 w-5 text-blue-600 focus:ring-blue-500 rounded"
                    />
                  </label>
                ))}
              </div>
              <button onClick={handleSaveNotifications} className="btn-primary">
                Save Changes
              </button>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="max-w-xl">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">Change Password</h2>
              <form onSubmit={handleChangePassword} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Current Password
                  </label>
                  <input
                    type="password"
                    value={passwordData.current}
                    onChange={(e) => setPasswordData({ ...passwordData, current: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    New Password
                  </label>
                  <input
                    type="password"
                    value={passwordData.new}
                    onChange={(e) => setPasswordData({ ...passwordData, new: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    required
                    minLength={8}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Confirm New Password
                  </label>
                  <input
                    type="password"
                    value={passwordData.confirm}
                    onChange={(e) => setPasswordData({ ...passwordData, confirm: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <button type="submit" className="btn-primary">
                  Change Password
                </button>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
