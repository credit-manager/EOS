import React from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';
import StatusBadge from '../components/StatusBadge';

export default function SystemHealthPage() {
  const { isRTL: _isRTL, t } = useI18n();
  const metrics = [
    { name: t.master.health.cpu, value: '45%', status: 'operational', color: '#22c55e' },
    { name: t.master.health.ram, value: '62%', status: 'warning', color: '#f59e0b' },
    { name: t.master.health.disk, value: '78%', status: 'warning', color: '#f59e0b' },
    { name: t.master.health.database, value: '12ms', status: 'operational', color: '#22c55e' },
    { name: t.master.health.apiLatency, value: '89ms', status: 'operational', color: '#22c55e' },
    { name: t.master.health.requestsPerSec, value: '1,240', status: 'operational', color: '#22c55e' },
    { name: t.master.health.errorRate, value: '0.02%', status: 'operational', color: '#22c55e' },
    { name: t.master.health.queue, value: '142', status: 'warning', color: '#f59e0b' },
  ];

  return (
    <AdminPage title={t.systemHealth.title} subtitle={t.systemHealth.subtitle}>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {metrics.map((m, i) => (
          <div key={i} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-500">{m.name}</span>
              <StatusBadge status={m.status} />
            </div>
            <p className="text-2xl font-bold text-gray-900">{m.value}</p>
            <div className="mt-2 h-2 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full rounded-full" style={{ width: m.name === t.master.health.cpu ? '45%' : m.name === t.master.health.ram ? '62%' : m.name === t.master.health.disk ? '78%' : '20%', backgroundColor: m.color }} />
            </div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">{t.systemHealth.systemIncidents}</h3>
          <div className="space-y-3">
            {[
              { title: t.systemHealth.elevatedDisk, status: 'warning', time: `1 ${t.dashboard.hoursAgo}` },
              { title: t.systemHealth.queueBacklog, status: 'warning', time: `3 ${t.dashboard.hoursAgo}` },
              { title: t.systemHealth.scheduledMaintenance, status: 'operational', time: `2 ${t.dashboard.daysAgo}`, resolved: true },
            ].map((inc, i) => (
              <div key={i} className="p-3 bg-gray-50 rounded-lg flex items-center justify-between">
                <div><p className="text-sm font-medium">{inc.title}</p><p className="text-xs text-gray-500">{inc.time}</p></div>
                <StatusBadge status={inc.resolved ? 'operational' : inc.status} />
              </div>
            ))}
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">{t.systemHealth.backgroundJobs}</h3>
          <div className="space-y-3">
            {[
              { name: t.systemHealth.dailyBackup, status: 'running', progress: 75 },
              { name: t.systemHealth.aiModelTraining, status: 'running', progress: 30 },
              { name: t.systemHealth.emailDispatch, status: 'completed', progress: 100 },
              { name: t.systemHealth.reportGeneration, status: 'queued', progress: 0 },
            ].map((job, i) => (
              <div key={i} className="p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">{job.name}</span>
                  <StatusBadge status={job.status} />
                </div>
                <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full" style={{ width: `${job.progress}%` }} />
                </div>
                <p className="text-xs text-gray-500 mt-1">{job.progress}%</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AdminPage>
  );
}
