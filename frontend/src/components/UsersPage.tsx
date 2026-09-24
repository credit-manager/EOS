import React, { useState, useEffect } from 'react';
import { TranslationKeys } from '../i18n';
import DataTable from './DataTable';
import Modal from './Modal';

interface User {
  id: string;
  email: string;
  role: string;
}

interface UsersPageProps {
  t: TranslationKeys;
  token: string;
}

export default function UsersPage({ t, token }: UsersPageProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [formData, setFormData] = useState({
    email: '',
    role: 'member',
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await fetch('/api/v1/auth/members', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        const rows = (Array.isArray(data) ? data : data.items || []).map(
          (u: Record<string, unknown>) => ({
            id: String(u.user_id ?? u.id ?? ''),
            email: String(u.email ?? ''),
            role: String(u.role ?? 'member'),
          })
        );
        setUsers(rows);
      }
    } catch {
      setError(t.common.error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingUser(null);
    setFormData({ email: '', role: 'member' });
    setShowModal(true);
  };

  const handleEdit = (user: User) => {
    setEditingUser(user);
    setFormData({ email: user.email, role: user.role });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingUser ? `/api/v1/auth/members/${editingUser.id}` : '/api/v1/auth/members';
      const method = editingUser ? 'PATCH' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ email: formData.email, role: formData.role }),
      });

      if (response.ok) {
        setShowModal(false);
        fetchUsers();
      } else {
        const data = await response.json();
        setError(data.detail || t.common.error);
      }
    } catch {
      setError(t.common.error);
    }
  };

  if (loading)
    return <div className="flex items-center justify-center h-64">{t.common.loading}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">{t.users.title}</h1>
        <button onClick={handleCreate} className="btn-primary">
          <span className="mr-2">+</span> {t.users.addMember}
        </button>
      </div>

      {error && <div className="alert-error">{error}</div>}

      <DataTable
        data={users}
        columns={[
          { key: 'email', header: t.users.title },
          {
            key: 'role',
            header: t.users.role,
            render: (row: User) => <RoleBadge role={row.role} t={t} />,
          },
        ]}
        onEdit={handleEdit}
        onDelete={undefined}
        t={t}
      />

      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={editingUser ? t.users.changeRole : t.users.addMember}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t.auth.email} *</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t.users.role} *</label>
            <select
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="admin">{t.users.admin}</option>
              <option value="member">{t.users.member}</option>
            </select>
          </div>
          <div className="flex justify-end gap-3 pt-4">
            <button type="button" onClick={() => setShowModal(false)} className="btn-secondary">
              {t.common.cancel}
            </button>
            <button type="submit" className="btn-primary">
              {t.common.save}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

function RoleBadge({ role, t }: { role: string; t: TranslationKeys }) {
  const roleMap: Record<string, { label: string; class: string }> = {
    admin: { label: t.users.admin, class: 'bg-purple-100 text-purple-800' },
    manager: { label: t.users.manager, class: 'bg-blue-100 text-blue-800' },
    member: { label: t.users.member, class: 'bg-green-100 text-green-800' },
    viewer: { label: t.users.viewer, class: 'bg-gray-100 text-gray-800' },
  };
  const s = roleMap[role] || { label: role, class: 'bg-gray-100 text-gray-800' };
  return <span className={`px-2 py-1 text-xs font-medium rounded-full ${s.class}`}>{s.label}</span>;
}
