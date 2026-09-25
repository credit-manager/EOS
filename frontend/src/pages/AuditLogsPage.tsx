import React, { useState, useEffect } from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';
import AdminTable from '../components/AdminTable';
import { getAuditEvents, type AuditEvent } from '../adminApi';

export default function AuditLogsPage() {
  const { isRTL: _isRTL, t } = useI18n();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterResult, setFilterResult] = useState('all');

  useEffect(() => {
    const token = localStorage.getItem('2to_eos_access_token');
    if (!token) return;
    setLoading(true);
    const params: { limit?: number; success?: boolean } = { limit: 100 };
    if (filterResult === 'success') params.success = true;
    if (filterResult === 'failed') params.success = false;
    getAuditEvents(token, params).then((res) => {
      setEvents(res.events || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [filterResult]);

  const c = t.master.common;
  const columns = [
    { key: 'id', header: 'ID', render: (e: AuditEvent) => <span className="font-mono text-xs">{e.id.slice(0, 8)}</span> },
    { key: 'user', header: t.master.auditLogs.user, render: (e: AuditEvent) => e.user },
    { key: 'tenant', header: t.master.auditLogs.tenant, render: (e: AuditEvent) => e.tenant },
    { key: 'action', header: t.master.auditLogs.action, render: (e: AuditEvent) => <code className="px-1.5 py-0.5 bg-gray-100 rounded text-xs">{e.action}</code> },
    { key: 'resource', header: t.master.auditLogs.resource, render: (e: AuditEvent) => e.resource },
    { key: 'timestamp', header: t.master.auditLogs.timestamp, render: (e: AuditEvent) => e.timestamp },
    { key: 'ip', header: t.master.auditLogs.ip, render: (e: AuditEvent) => <span className="font-mono text-xs">{e.ip}</span> },
    { key: 'result', header: t.master.auditLogs.filters.success, render: (e: AuditEvent) => e.result === 'success' ? '✅' : '❌' },
  ];

  return (
    <AdminPage title={t.master.auditLogs.title} subtitle={t.master.auditLogs.user}>
      <div className="flex gap-4 mb-6">
        <select className="px-3 py-2 border border-gray-300 rounded-lg text-sm" value={filterResult} onChange={(e) => setFilterResult(e.target.value)}>
          <option value="all">{c.all}</option>
          <option value="success">{c.success}</option>
          <option value="failed">{c.failed}</option>
        </select>
        <input type="text" placeholder={c.search} className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm" />
      </div>
      {loading ? (
        <div className="text-center py-12 text-gray-500">{c.loading}</div>
      ) : (
        <AdminTable columns={columns} data={events} />
      )}
    </AdminPage>
  );
}
