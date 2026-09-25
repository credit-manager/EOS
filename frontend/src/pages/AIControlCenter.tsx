import React, { useState, useEffect } from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';
import { getAIStats, type AIStats } from '../adminApi';

export default function AIControlCenter() {
  const { isRTL: _isRTL, t } = useI18n();
  const [stats, setStats] = useState<AIStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('2to_eos_access_token');
    if (!token) return;
    setLoading(true);
    getAIStats(token).then((res) => setStats(res)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const c = t.master.common;
  const statCards = stats ? [
    { title: t.master.aiControl.requests, value: stats.apiRequests.toLocaleString() },
    { title: t.master.aiControl.models, value: String(stats.totalLlmConfigs) },
    { title: t.master.aiControl.latency, value: `${stats.avgLatencyMs}ms` },
    { title: t.master.aiControl.cost, value: `$${stats.cost.toLocaleString()}` },
  ] : [
    { title: t.master.aiControl.requests, value: '-' },
    { title: t.master.aiControl.models, value: '-' },
    { title: t.master.aiControl.latency, value: '-' },
    { title: t.master.aiControl.cost, value: '-' },
  ];

  return (
    <AdminPage title={t.master.aiControl.title} subtitle={t.master.aiControl.models}>
      <div className="grid grid-cols-4 gap-4 mb-6">
        {statCards.map((stat, i) => (
          <div key={i} className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500">{stat.title}</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
          </div>
        ))}
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{t.master.aiControl.models}</h3>
        {loading ? (
          <div className="text-center py-8 text-gray-500">{c.loading}</div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            {stats && stats.totalLlmConfigs > 0 ? `${stats.totalLlmConfigs} ${t.master.aiControl.models}` : c.noData}
          </div>
        )}
      </div>
    </AdminPage>
  );
}
