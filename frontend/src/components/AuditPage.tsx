import React, { useState, useEffect } from 'react';
import { useI18n } from '../i18n';
import DataTable from './DataTable';

interface AuditEntry {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  actor_id: string;
  created_at: string;
  metadata: Record<string, unknown>;
}

interface AuditPageProps {
  token: string;
}

export default function AuditPage({ token }: AuditPageProps) {
  const { t } = useI18n();
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ action: '', resource_type: '' });

  useEffect(() => {
    fetchEntries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  const fetchEntries = async () => {
    try {
      const params = new URLSearchParams();
      if (filter.action) params.append('action', filter.action);
      if (filter.resource_type) params.append('resource_type', filter.resource_type);

      const response = await fetch(`/api/v1/audit/events?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setEntries(Array.isArray(data) ? data : data.items || []);
      }
    } catch (err) {
      console.error('Failed to fetch audit:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64">{t.common.loading}</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">{t.auditPage.title}</h1>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t.auditPage.actionLabel}</label>
            <input
              type="text"
              value={filter.action}
              onChange={(e) => setFilter({ ...filter, action: e.target.value })}
              placeholder={t.auditPage.filterByAction}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t.auditPage.resourceType}</label>
            <input
              type="text"
              value={filter.resource_type}
              onChange={(e) => setFilter({ ...filter, resource_type: e.target.value })}
              placeholder={t.auditPage.filterByResource}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={() => setFilter({ action: '', resource_type: '' })}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
            >
              {t.auditPage.clear}
            </button>
          </div>
        </div>
      </div>

      <DataTable
        data={entries}
        columns={[
          { key: 'action', header: t.auditPage.action, className: 'max-w-xs truncate' },
          { key: 'resource_type', header: t.auditPage.resourceType },
          { key: 'resource_id', header: t.auditPage.resourceId, className: 'font-mono text-xs' },
          { key: 'actor_id', header: t.auditPage.actor, className: 'font-mono text-xs' },
          {
            key: 'created_at',
            header: t.auditPage.timestamp,
            render: (row: AuditEntry) => formatDate(row.created_at),
            className: 'whitespace-nowrap',
          },
          {
            key: 'metadata',
            header: t.auditPage.details,
            render: (row: AuditEntry) => (
              <button
                onClick={() => alert(JSON.stringify(row.metadata, null, 2))}
                className="text-blue-600 hover:text-blue-800 text-sm underline"
              >
                {t.auditPage.view}
              </button>
            ),
          },
        ]}
        onEdit={() => {}}
        onDelete={() => {}}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        t={{} as any}
      />
    </div>
  );
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('ar-SA', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}
