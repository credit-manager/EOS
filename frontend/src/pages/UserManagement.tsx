import React, { useState, useEffect } from 'react';
import { useI18n } from '../i18n';
import AdminTable from '../components/AdminTable';
import StatusBadge from '../components/StatusBadge';
import AdminPage from '../components/AdminPage';
import { getUsers, type User } from '../adminApi';

export default function UserManagement() {
  const { isRTL: _isRTL, t } = useI18n();
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('2to_eos_access_token');
    if (!token) return;
    setLoading(true);
    getUsers(token).then((res) => {
      setUsers(res.users);
      setTotal(res.total);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const c = t.master.common;
  const columns = [
    { key: 'id', header: 'ID', render: (u: User) => <span className="font-mono text-xs">{u.id.slice(0, 8)}</span> },
    { key: 'email', header: t.master.users.user, render: (u: User) => <span className="font-medium">{u.email}</span> },
    { key: 'tenant', header: t.master.users.tenant, render: (u: User) => <span className="font-mono text-xs">{u.tenant ? u.tenant.slice(0, 8) : '-'}</span> },
    { key: 'role', header: t.master.users.role, render: (u: User) => <span className="px-2 py-0.5 bg-purple-50 text-purple-700 rounded text-xs">{u.role}</span> },
    { key: 'status', header: t.master.users.status, render: (u: User) => <StatusBadge status={u.status} /> },
    { key: 'mfa', header: t.master.users.mfa, render: (u: User) => u.mfa ? '✅' : '❌' },
    { key: 'lastLogin', header: t.master.users.lastLogin, render: (u: User) => u.lastLogin || 'Never' },
    { key: 'sessions', header: t.master.users.sessions, render: (u: User) => u.sessions },
    { key: 'riskStatus', header: t.master.users.riskStatus, render: (u: User) => u.riskStatus === 'high' ? '🔴 High' : u.riskStatus === 'medium' ? '🟡 Medium' : '🟢 Low' },
    { key: 'actions', header: c.actions, render: (_u: User) => (
      <div className="flex gap-1">
        <button className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded">{c.view}</button>
        <button className="px-2 py-1 text-xs bg-yellow-100 text-yellow-700 rounded">{c.edit}</button>
        <button className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded">{c.suspend}</button>
        <button className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">{t.master.users.forceLogout}</button>
      </div>
    )},
  ];

  return (
    <AdminPage title={t.master.users.title} subtitle={t.master.users.searchPlaceholder}>
      <div className="flex gap-4 mb-6">
        <input type="text" placeholder={t.master.users.searchPlaceholder}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
          value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">+ {c.new} User</button>
      </div>
      {loading ? (
        <div className="text-center py-12 text-gray-500">{c.loading}</div>
      ) : (
        <>
          <div className="text-sm text-gray-500 mb-2">{c.total}: {total}</div>
          <AdminTable columns={columns} data={users} />
        </>
      )}
    </AdminPage>
  );
}
