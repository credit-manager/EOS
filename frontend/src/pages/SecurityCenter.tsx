import React from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';
import StatusBadge from '../components/StatusBadge';

export default function SecurityCenter() {
  const { isRTL: _isRTL, t } = useI18n();
  const securityEvents = [
    { type: 'login_attempt', user: 'admin@acme.com', ip: '192.168.1.1', result: 'success', time: '2 min ago', device: 'Chrome / Windows' },
    { type: 'login_attempt', user: 'unknown@temp.com', ip: '10.0.0.5', result: 'failed', time: '5 min ago', device: 'Firefox / Linux' },
    { type: 'suspicious', user: 'unknown@temp.com', ip: '10.0.0.5', result: 'blocked', time: '5 min ago', device: 'Firefox / Linux' },
  ];

  return (
    <AdminPage title={t.securityCenter.title} subtitle={t.securityCenter.subtitle}>
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { title: t.master.security.loginAttempts, value: '12,450', color: 'blue' },
          { title: t.master.security.failedLogins, value: '342', color: 'red' },
          { title: t.master.security.activeSessions, value: '89', color: 'green' },
          { title: t.master.security.blockIP, value: '23', color: 'orange' },
        ].map((s, i) => (
          <div key={i} className={`rounded-xl border p-4 ${s.color === 'red' ? 'bg-red-50 border-red-200' : 'bg-white border-gray-200'}`}>
            <p className="text-xs text-gray-500">{s.title}</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{s.value}</p>
          </div>
        ))}
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{t.securityCenter.recentEvents}</h3>
        <table className="min-w-full text-sm">
          <thead><tr className="border-b border-gray-200"><th className="text-left p-3">{t.securityCenter.type}</th><th className="text-left p-3">{t.securityCenter.user}</th><th className="text-left p-3">{t.securityCenter.ip}</th><th className="text-left p-3">{t.securityCenter.result}</th><th className="text-left p-3">{t.securityCenter.time}</th><th className="text-left p-3">{t.securityCenter.device}</th></tr></thead>
          <tbody>
            {securityEvents.map((ev, i) => (
              <tr key={i} className="border-t border-gray-100">
                <td className="p-3">{ev.type}</td>
                <td className="p-3">{ev.user}</td>
                <td className="p-3 font-mono text-xs">{ev.ip}</td>
                <td className="p-3"><StatusBadge status={ev.result === 'success' ? 'active' : ev.result === 'failed' ? 'suspended' : 'critical'} /></td>
                <td className="p-3">{ev.time}</td>
                <td className="p-3">{ev.device}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AdminPage>
  );
}
