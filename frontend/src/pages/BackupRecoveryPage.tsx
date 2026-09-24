import React from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';
import StatusBadge from '../components/StatusBadge';

export default function BackupRecoveryPage() {
  const { isRTL: _isRTL, t } = useI18n();
  const backups = [
    { id: 'B-001', type: 'Database', size: '2.1GB', status: 'completed', date: '2026-09-20', duration: '45 min' },
    { id: 'B-002', type: 'File', size: '890MB', status: 'completed', date: '2026-09-19', duration: '12 min' },
    { id: 'B-003', type: 'Database', size: '2.0GB', status: 'failed', date: '2026-09-18', duration: '-' },
  ];

  return (
    <AdminPage title={t.backupRecovery.title} subtitle={t.backupRecovery.subtitle}>
      <div className="flex justify-between mb-6">
        <div className="flex gap-4">
          <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-2">
            <p className="text-xs text-green-700">{t.backupRecovery.lastBackup}</p>
            <p className="text-lg font-bold text-green-900">2h ago</p>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2">
            <p className="text-xs text-blue-700">{t.backupRecovery.totalBackups}</p>
            <p className="text-lg font-bold text-blue-900">142</p>
          </div>
        </div>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">+ {t.backupRecovery.createBackup}</button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50"><tr><th className="text-left p-3">{t.backupRecovery.id}</th><th className="text-left p-3">{t.backupRecovery.type}</th><th className="text-left p-3">{t.backupRecovery.size}</th><th className="text-left p-3">{t.backupRecovery.status}</th><th className="text-left p-3">{t.backupRecovery.date}</th><th className="text-left p-3">{t.backupRecovery.duration}</th><th className="text-left p-3">Actions</th></tr></thead>
          <tbody>
            {backups.map((b, i) => (
              <tr key={i} className="border-t border-gray-100">
                <td className="p-3 font-mono text-xs">{b.id}</td>
                <td className="p-3">{b.type}</td>
                <td className="p-3">{b.size}</td>
                <td className="p-3"><StatusBadge status={b.status === 'completed' ? 'operational' : 'critical'} /></td>
                <td className="p-3">{b.date}</td>
                <td className="p-3">{b.duration}</td>
                <td className="p-3"><div className="flex gap-1"><button className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded">{t.backupRecovery.restore}</button><button className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded">Delete</button></div></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AdminPage>
  );
}
