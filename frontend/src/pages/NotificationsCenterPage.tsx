import React from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';
import StatusBadge from '../components/StatusBadge';

export default function NotificationsCenterPage() {
  const { isRTL: _isRTL, t } = useI18n();
  const notifications = [
    { title: 'Platform maintenance scheduled', type: 'maintenance', scope: 'Global', time: '1 hr ago' },
    { title: 'New tenant onboarding', type: 'info', scope: 'Tenant-specific', time: '30 min ago' },
    { title: 'Suspicious login attempt', type: 'security', scope: 'User-specific', time: '2 min ago' },
  ];

  return (
    <AdminPage title={t.notificationsCenter.title} subtitle={t.notificationsCenter.subtitle}>
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{t.notificationsCenter.sendNotification}</h3>
        <div className="space-y-4">
          <input type="text" placeholder={t.notificationsCenter.notificationTitle} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          <textarea placeholder={t.notificationsCenter.message} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm h-24" />
          <div className="flex gap-4">
            <select className="px-3 py-2 border border-gray-300 rounded-lg text-sm"><option>{t.notificationsCenter.scope}</option></select>
            <select className="px-3 py-2 border border-gray-300 rounded-lg text-sm"><option>{t.notificationsCenter.category}</option></select>
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">{t.notificationsCenter.send}</button>
          </div>
        </div>
      </div>
      <div className="space-y-3">
        {notifications.map((n, i) => (
          <div key={i} className="bg-white rounded-xl border border-gray-200 p-4 flex items-center justify-between">
            <div><p className="font-medium text-gray-900">{n.title}</p><p className="text-xs text-gray-500">{n.scope} · {n.time}</p></div>
            <StatusBadge status={n.type === 'security' ? 'critical' : n.type === 'maintenance' ? 'warning' : 'operational'} />
          </div>
        ))}
      </div>
    </AdminPage>
  );
}
