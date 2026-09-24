import React, { useState, useEffect } from 'react';
import { useI18n } from '../i18n';
import StatCard from '../components/StatCard';
import StatusBadge from '../components/StatusBadge';
import AdminPage from '../components/AdminPage';
import { getHealth, getTenants, getUsers, getPlans } from '../adminApi';

export default function MasterDashboard() {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<'overview' | 'health' | 'charts'>('overview');
  const [tenants, setTenants] = useState<{id: string; name: string; owner: string; industry: string; country: string; plan: string; status: string; users: number; storage: string; aiUsage: string; createdAt: string; lastActive: string}[]>([]);
  const [users, setUsers] = useState<{id: string; email: string; tenant: string; role: string; status: string; mfa: boolean; lastLogin: string; created: string; sessions: number; riskStatus: string}[]>([]);

  useEffect(() => {
    const token = localStorage.getItem('2to_eos_access_token');
    if (token) {
      getHealth(token).then(_h => {}).catch(() => {});
      getTenants(token).then(r => setTenants(r.tenants)).catch(() => {});
      getUsers(token).then(r => setUsers(r.users)).catch(() => {});
      getPlans(token).then(_r => {}).catch(() => {});
    }
  }, []);

  const tenantCount = tenants.length;
  const activeTenantCount = tenants.filter((t) => t.status === 'active').length;
  const userCount = users.length;

  const kpiData = [
    { title: t.master.overview.totalTenants, value: tenantCount, icon: '🏢', color: 'blue', change: '+12%', changeType: 'up' },
    { title: t.master.overview.activeTenants, value: activeTenantCount, icon: '✅', color: 'green', change: '+8%', changeType: 'up' },
    { title: t.master.overview.suspendedTenants, value: tenantCount - activeTenantCount, icon: '⛔', color: 'red', change: '+3%', changeType: 'down' },
    { title: t.master.overview.totalUsers, value: userCount, icon: '👥', color: 'purple', change: '+15%', changeType: 'up' },
    { title: t.master.overview.mrr, value: '$142,580', icon: '💰', color: 'green', change: '+22%', changeType: 'up' },
    { title: t.master.overview.arr, value: '$1.71M', icon: '📈', color: 'indigo', change: '+22%', changeType: 'up' },
    { title: t.master.overview.revenue, value: '$284K', icon: '💵', color: 'teal', change: '+18%', changeType: 'up' },
    { title: t.master.overview.outstandingPayments, value: '$38,420', icon: '⚠️', color: 'orange', change: '+5%', changeType: 'down' },
    { title: t.master.overview.aiUsage, value: '87%', icon: '🤖', color: 'purple', change: '+34%', changeType: 'up' },
    { title: t.master.overview.apiUsage, value: '1.2M', icon: '🔑', color: 'blue', change: '+19%', changeType: 'up' },
    { title: t.master.overview.automationRuns, value: '45.2K', icon: '⚙️', color: 'teal', change: '+28%', changeType: 'up' },
    { title: t.master.overview.storageUsage, value: '68%', icon: '💾', color: 'orange', change: '+3%', changeType: 'up' },
  ];

  const healthChecks = [
    { name: t.master.health.apiStatus, status: 'operational', details: '99.9% uptime' },
    { name: t.master.health.databaseStatus, status: 'operational', details: 'PostgreSQL 16 · 12ms avg' },
    { name: t.master.health.aiServicesStatus, status: 'operational', details: 'OpenAI · Claude · Local' },
    { name: t.master.health.backgroundJobs, status: 'operational', details: '12 workers active' },
    { name: t.master.health.queueStatus, status: 'warning', details: '142 pending (normal)' },
    { name: t.master.health.storageStatus, status: 'operational', details: '4.2TB / 10TB (42%)' },
    { name: t.master.health.emailService, status: 'operational', details: 'SendGrid · 99.8%' },
    { name: t.master.health.paymentGateway, status: 'operational', details: 'Stripe · All clear' },
    { name: t.master.health.externalIntegrations, status: 'operational', details: '14/14 connected' },
  ];

  return (
    <AdminPage title={t.master.title} subtitle={t.master.subtitle}>
      <div className="flex gap-2 mb-6">
        {(['overview', 'health', 'charts'] as const).map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-medium capitalize ${activeTab === tab ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
            {tab === 'overview' ? t.master.overview.title : tab === 'health' ? t.master.health.title : t.master.overview.analyticsTab}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
            {kpiData.map((kpi, i) => (
              <StatCard key={i} {...kpi} />
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">{t.dashboard.systemHealth}</h3>
              <div className="space-y-3">
                {healthChecks.map((check, i) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{check.name}</p>
                      <p className="text-xs text-gray-500">{check.details}</p>
                    </div>
                    <StatusBadge status={check.status} />
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">{t.dashboard.recentActivity}</h3>
              <div className="space-y-3">
                {[
                  { action: t.dashboard.newTenantRegistered, user: 'System', time: `2 ${t.dashboard.minutesAgo}`, icon: '🏢' },
                  { action: t.dashboard.paymentProcessed, user: 'Stripe', time: `5 ${t.dashboard.minutesAgo}`, icon: '💳' },
                  { action: t.dashboard.aiModelUpdated, user: 'System', time: `12 ${t.dashboard.minutesAgo}`, icon: '🤖' },
                  { action: t.dashboard.userSuspended, user: 'Admin', time: `25 ${t.dashboard.minutesAgo}`, icon: '👤' },
                  { action: t.dashboard.backupCompleted, user: 'System', time: `1 ${t.dashboard.hoursAgo}`, icon: '💾' },
                ].map((activity, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                    <span className="text-xl">{activity.icon}</span>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{activity.action}</p>
                      <p className="text-xs text-gray-500">{activity.user} · {activity.time}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}

      {activeTab === 'health' && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">{t.dashboard.allSystems}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {healthChecks.map((check, i) => (
              <div key={i} className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-gray-900">{check.name}</span>
                  <StatusBadge status={check.status} />
                </div>
                <p className="text-xs text-gray-500">{check.details}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'charts' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[
            { title: t.dashboard.revenueGrowth, color: '#22c55e' },
            { title: t.dashboard.tenantGrowth, color: '#3b82f6' },
            { title: t.dashboard.userGrowth, color: '#8b5cf6' },
            { title: t.dashboard.aiUsage, color: '#f59e0b' },
          ].map((chart, i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">{chart.title}</h3>
              <div className="h-48 flex items-end gap-1">
                {[65, 45, 78, 55, 90, 72, 85, 60, 95, 80, 70, 88].map((h, j) => (
                  <div key={j} className="flex-1 rounded-t" style={{ height: `${h}%`, backgroundColor: chart.color, opacity: 0.6 + (j / 12) * 0.4 }} />
                ))}
              </div>
              <div className="flex justify-between mt-2 text-xs text-gray-400">
                <span>Jan</span><span>Jun</span><span>Dec</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </AdminPage>
  );
}
