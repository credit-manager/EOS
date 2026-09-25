import React, { useState, useEffect } from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';
import StatusBadge from '../components/StatusBadge';

interface RoleData {
  name: string;
  permissions: string[];
}

export default function RolesPermissions() {
  const { isRTL: _isRTL, t } = useI18n();
  const [roles, setRoles] = useState<RoleData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('2to_eos_access_token');
    if (!token) return;
    setLoading(true);
    fetch('/api/v1/permissions/roles', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        const roleList: RoleData[] = Object.entries(data).map(([name, perms]) => ({
          name,
          permissions: Array.isArray(perms) ? perms.map(String) : [],
        }));
        setRoles(roleList);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const c = t.master.common;

  return (
    <AdminPage title={t.master.roles.title} subtitle={t.master.roles.permissions}>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">{t.master.roles.systemRoles}</h3>
          {loading ? (
            <div className="text-center py-8 text-gray-500">{c.loading}</div>
          ) : (
            <div className="space-y-3">
              {roles.map((role, i) => (
                <div key={i} className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-gray-900">{role.name}</span>
                    <StatusBadge status="active" />
                  </div>
                  <p className="text-xs text-gray-500 mb-2">{role.permissions.length} {t.master.roles.permissions}</p>
                  <div className="flex flex-wrap gap-1">
                    {role.permissions.slice(0, 5).map((p, j) => (
                      <span key={j} className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">{p}</span>
                    ))}
                    {role.permissions.length > 5 && (
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">+{role.permissions.length - 5}</span>
                    )}
                  </div>
                </div>
              ))}
              {roles.length === 0 && (
                <div className="text-center py-8 text-gray-500">{c.noData}</div>
              )}
            </div>
          )}
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">{t.master.roles.permissions}</h3>
          <div className="text-sm text-gray-500">
            <p>{t.master.roles.systemRoles}</p>
            <p className="mt-2">{t.master.roles.tenantRoles}</p>
          </div>
        </div>
      </div>
    </AdminPage>
  );
}
