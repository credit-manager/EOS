import React, { useState, useEffect } from 'react';
import { TranslationKeys } from '../i18n';

interface DashboardStats {
  total_projects: number;
  active_projects: number;
  total_budget: number;
  total_entries: number;
}

interface DashboardProps {
  t: TranslationKeys;
  token: string;
}

export default function Dashboard({ t, token }: DashboardProps) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/v1/reports/dashboard', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch dashboard stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">{t.common.loading}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">{t.dashboard.title}</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title={t.dashboard.totalProjects}
          value={stats?.total_projects ?? 0}
          color="blue"
        />
        <StatCard
          title={t.dashboard.activeProjects}
          value={stats?.active_projects ?? 0}
          color="green"
        />
        <StatCard
          title={t.dashboard.totalBudget}
          value={stats?.total_budget ?? 0}
          color="purple"
          format="currency"
        />
        <StatCard
          title={t.dashboard.totalEntries}
          value={stats?.total_entries ?? 0}
          color="orange"
        />
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  color,
  format,
}: {
  title: string;
  value: number;
  color: string;
  format?: string;
}) {
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    orange: 'bg-orange-50 text-orange-600',
  };

  const displayValue =
    format === 'currency'
      ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'SAR' }).format(value)
      : value.toLocaleString();

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div
        className={`inline-flex items-center justify-center w-12 h-12 rounded-lg ${colorClasses[color]}`}
      >
        <span className="text-xl font-bold">{displayValue.charAt(0)}</span>
      </div>
      <h3 className="mt-4 text-sm font-medium text-gray-500">{title}</h3>
      <p className="mt-2 text-3xl font-bold text-gray-900">{displayValue}</p>
    </div>
  );
}
