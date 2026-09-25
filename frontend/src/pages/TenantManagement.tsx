import React, { useState, useEffect } from 'react';
import { useI18n } from '../i18n';
import AdminTable from '../components/AdminTable';
import StatusBadge from '../components/StatusBadge';
import ConfirmDialog from '../components/ConfirmDialog';
import AdminPage from '../components/AdminPage';
import { getTenants, type Tenant } from '../adminApi';

export default function TenantManagement() {
  const { isRTL: _isRTL, t } = useI18n();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showConfirm, setShowConfirm] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('2to_eos_access_token');
    if (!token) return;
    setLoading(true);
    getTenants(token).then((res) => {
      setTenants(res.tenants);
      setTotal(res.total);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const c = t.master.common;
  const columns = [
    { key: 'id', header: 'ID', render: (x: Tenant) => <span className="font-mono text-xs">{x.id.slice(0, 8)}</span> },
    { key: 'name', header: t.master.tenants.companyName, render: (x: Tenant) => <span className="font-medium">{x.name}</span> },
    { key: 'industry', header: t.master.tenants.industry, render: (x: Tenant) => x.industry || '-' },
    { key: 'country', header: t.master.tenants.country, render: (x: Tenant) => x.country || '-' },
    { key: 'plan', header: t.master.tenants.plan, render: (x: Tenant) => <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">{x.plan || 'Free'}</span> },
    { key: 'status', header: t.master.tenants.status, render: (x: Tenant) => <StatusBadge status={x.status} /> },
    { key: 'users', header: t.master.tenants.users, render: (x: Tenant) => x.users },
    { key: 'storage', header: t.master.tenants.storage, render: (x: Tenant) => x.storage },
    { key: 'aiUsage', header: 'AI', render: (x: Tenant) => x.aiUsage },
    { key: 'lastActive', header: c.lastActive, render: (x: Tenant) => x.lastActive || '-' },
    { key: 'actions', header: c.actions, render: (x: Tenant) => (
      <div className="flex gap-1">
        <button className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200">{c.view}</button>
        <button className="px-2 py-1 text-xs bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200">{c.edit}</button>
        <button className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200" onClick={() => { setSelectedTenant(x); setShowConfirm(true); }}>{c.suspend}</button>
      </div>
    )},
  ];

  return (
    <AdminPage title={t.master.tenants.title} subtitle={t.master.tenants.searchPlaceholder}>
      <div className="flex gap-4 mb-6">
        <input type="text" placeholder={t.master.tenants.searchPlaceholder}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
          value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">+ {c.new} Tenant</button>
      </div>
      {loading ? (
        <div className="text-center py-12 text-gray-500">{c.loading}</div>
      ) : (
        <>
          <div className="text-sm text-gray-500 mb-2">{c.total}: {total}</div>
          <AdminTable columns={columns} data={tenants} onRowClick={(x) => console.log(x)} />
        </>
      )}
      <ConfirmDialog isOpen={showConfirm} onClose={() => setShowConfirm(false)} onConfirm={() => setShowConfirm(false)} title={c.suspend} message={`Suspend ${selectedTenant?.name}?`} confirmText={c.confirm} variant="danger" />
    </AdminPage>
  );
}
