import React, { useState, useEffect } from 'react';
import { TranslationKeys } from '../i18n';
import DataTable from './DataTable';

interface AuditEntry {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  actor_id: string;
  created_at: string;
  metadata: Record<string, any>;
}

interface AuditPageProps {
  t: TranslationKeys;
  token: string;
}

export default function AuditPage({ t, token }: AuditPageProps) {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ action: '', resource: '', date_from: '', date_to: '' });

  const columns = [
    { key: 'action', header: 'Action', className: 'max-w-xs truncate' },
    { key: 'resource_type', header: 'Resource Type' },
    { key: 'resource_id', header: 'Resource ID', className: 'font-mono text-xs' },
    { key: 'actor_id', header: 'Actor', className: 'font-mono text-xs' },
    { key: 'created_at', header: 'Timestamp', render: (row: AuditEntry) => formatDate(row.created_at), className: 'whitespace-nowrap' },
    { key: 'metadata', header: 'Details', render: (row: AuditEntry) => (
      <button
        onClick={() => alert(JSON.stringify(row.metadata, null, 2))}
        className="text-blue-600 hover:text-blue-800 text-sm underline"
      >
        View
      </button>
    )},
  ];

  useEffect(() => {
    fetchEntries();
  }, [filter]);

  const fetchEntries = async () => {
    try {
      const params = new URLSearchParams();
      if (filter.action) params.append('action', filter.action);
      if (filter.resource) params.append('resource', filter.resource);
      if (filter.date_from) params.append('date_from', filter.date_from);
      if (filter.date_to) params.append('date_to', filter.date_to);

      const response = await fetch(`/api/v1/audit?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setEntries(data.items || []);
      }
    } catch (err) {
      console.error('Failed to fetch audit:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64">Loading...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Action</label>
            <input
              type="text"
              value={filter.action}
              onChange={(e) => setFilter({ ...filter, action: e.target.value })}
              placeholder="Filter by action..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Resource Type</label>
            <input
              type="text"
              value={filter.resource}
              onChange={(e) => setFilter({ ...filter, resource: e.target.value })}
              placeholder="Filter by resource..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Date From</label>
            <input
              type="date"
              value={filter.date_from}
              onChange={(e) => setFilter({ ...filter, date_from: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Date To</label>
            <input
              type="date"
              value={filter.date_to}
              onChange={(e) => setFilter({ ...filter, date_to: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      <DataTable
        data={entries}
        columns={[
          { key: 'action', header: 'Action', className: 'max-w-xs truncate' },
          { key: 'resource_type', header: 'Resource Type' },
          { key: 'resource_id', header: 'Resource ID', className: 'font-mono text-xs' },
          { key: 'actor_id', header: 'Actor', className: 'font-mono text-xs' },
          { key: 'created_at', header: 'Timestamp', render: (row: AuditEntry) => formatDate(row.created_at), className: 'whitespace-nowrap' },
          { key: 'metadata', header: 'Details', render: (row: AuditEntry) => (
            <button
              onClick={() => alert(JSON.stringify(row.metadata, null, 2))}
              className="text-blue-600 hover:text-blue-800 text-sm underline"
            >
              View
            </button>
          )},
        ]}
        onEdit={() => {}}
        onDelete={() => {}}
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
    second: '2-digit'
  });
}