import React, { useState, useEffect } from 'react';
import { TranslationKeys } from '../i18n';
import DataTable from './DataTable';
import Modal from './Modal';
import ConfirmDialog from './ConfirmDialog';

interface Contract {
  id: string;
  number: string;
  project_id: string;
  project_name: string;
  total_amount: string;
  status: string;
}

interface ContractsPageProps {
  t: TranslationKeys;
  token: string;
}

export default function ContractsPage({ t, token }: ContractsPageProps) {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [projects, setProjects] = useState<{ id: string; name: string; code: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingContract, setEditingContract] = useState<Contract | null>(null);
  const [formData, setFormData] = useState({
    number: '',
    project_id: '',
    total_amount: '',
    status: 'draft',
  });
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const columns = [
    { key: 'number', header: t.contracts.number },
    { key: 'project_name', header: t.contracts.projectName },
    {
      key: 'total_amount',
      header: t.contracts.totalAmount,
      render: (row: Contract) => (
        <span className="font-mono">{formatCurrency(row.total_amount)}</span>
      ),
    },
    {
      key: 'status',
      header: t.contracts.status,
      render: (row: Contract) => <StatusBadge status={row.status} t={t} />,
    },
  ];

  useEffect(() => {
    fetchContracts();
    fetchProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchContracts = async () => {
    try {
      const response = await fetch('/api/v1/construction/contracts', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setContracts(data.items || data);
      }
    } catch {
      setError(t.common.error);
    } finally {
      setLoading(false);
    }
  };

  const fetchProjects = async () => {
    try {
      const response = await fetch('/api/v1/construction/projects', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setProjects(data.items || data);
      }
    } catch {
      // ignore
    }
  };

  const handleCreate = () => {
    setEditingContract(null);
    setFormData({ number: '', project_id: '', total_amount: '', status: 'draft' });
    setShowModal(true);
  };

  const handleEdit = (contract: Contract) => {
    setEditingContract(contract);
    setFormData({ ...contract });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingContract
        ? `/api/v1/construction/contracts/${editingContract.id}`
        : '/api/v1/construction/contracts';
      const method = editingContract ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setShowModal(false);
        fetchContracts();
      } else {
        const data = await response.json();
        setError(data.detail || t.common.error);
      }
    } catch {
      setError(t.common.error);
    }
  };

  const handleDelete = (id: string) => setDeleteConfirm(id);

  const confirmDelete = async () => {
    if (!deleteConfirm) return;
    try {
      const response = await fetch(`/api/v1/construction/contracts/${deleteConfirm}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) fetchContracts();
    } finally {
      setDeleteConfirm(null);
    }
  };

  if (loading)
    return <div className="flex items-center justify-center h-64">{t.common.loading}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">{t.contracts.title}</h1>
        <button onClick={handleCreate} className="btn-primary">
          <span className="mr-2">+</span> {t.contracts.create}
        </button>
      </div>

      {error && <div className="alert-error">{error}</div>}

      <DataTable
        data={contracts}
        columns={columns}
        onEdit={handleEdit}
        onDelete={handleDelete}
        t={t}
      />

      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={editingContract ? t.contracts.edit : t.contracts.create}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t.contracts.number} *
            </label>
            <input
              type="text"
              value={formData.number}
              onChange={(e) => setFormData({ ...formData, number: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t.contracts.projectName} *
            </label>
            <select
              value={formData.project_id}
              onChange={(e) => setFormData({ ...formData, project_id: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="">{t.common.selectAll}</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.code})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t.contracts.totalAmount} *
            </label>
            <input
              type="number"
              step="0.01"
              value={formData.total_amount}
              onChange={(e) => setFormData({ ...formData, total_amount: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t.contracts.status}
            </label>
            <select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="draft">{t.contracts.draft}</option>
              <option value="active">{t.contracts.active}</option>
              <option value="completed">{t.contracts.completed}</option>
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

      <ConfirmDialog
        isOpen={!!deleteConfirm}
        onClose={() => setDeleteConfirm(null)}
        onConfirm={confirmDelete}
        title={t.common.confirm}
        message={t.common.confirm}
      />
    </div>
  );
}

function StatusBadge({ status, t }: { status: string; t: TranslationKeys }) {
  const statusMap: Record<string, { label: string; class: string }> = {
    draft: { label: t.contracts.draft, class: 'bg-gray-100 text-gray-800' },
    active: { label: t.contracts.active, class: 'bg-green-100 text-green-800' },
    completed: { label: t.contracts.completed, class: 'bg-blue-100 text-blue-800' },
  };
  const s = statusMap[status] || { label: status, class: 'bg-gray-100 text-gray-800' };
  return <span className={`px-2 py-1 text-xs font-medium rounded-full ${s.class}`}>{s.label}</span>;
}

function formatCurrency(value: string): string {
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  return new Intl.NumberFormat('ar-SA', { style: 'currency', currency: 'SAR' }).format(num);
}
