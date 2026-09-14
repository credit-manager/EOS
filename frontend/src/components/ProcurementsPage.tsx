import React, { useState, useEffect } from 'react';
import { TranslationKeys } from '../i18n';
import DataTable from './DataTable';
import Modal from './Modal';
import ConfirmDialog from './ConfirmDialog';

interface Procurement {
  id: string;
  description: string;
  vendor: string;
  amount: string;
  status: string;
}

interface ProcurementsPageProps {
  t: TranslationKeys;
  token: string;
}

export default function ProcurementsPage({ t, token }: ProcurementsPageProps) {
  const [items, setItems] = useState<Procurement[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingItem, setEditingItem] = useState<Procurement | null>(null);
  const [formData, setFormData] = useState({
    description: '',
    vendor: '',
    amount: '',
    status: 'draft',
  });
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchItems();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchItems = async () => {
    try {
      const response = await fetch('/api/v1/construction/procurements', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setItems(data.items || data);
      }
    } catch {
      setError(t.common.error);
    } finally {
      setLoading(false);
    }
  };

  const _handleCreate = () => {
    setEditingItem(null);
    setFormData({ description: '', vendor: '', amount: '', status: 'draft' });
    setShowModal(true);
  };

  const handleEdit = (item: Procurement) => {
    setEditingItem(item);
    setFormData({ ...item });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingItem
        ? `/api/v1/construction/procurements/${editingItem.id}`
        : '/api/v1/construction/procurements';
      const method = editingItem ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setShowModal(false);
        fetchItems();
      } else {
        const data = await response.json();
        setError(data.detail || t.common.error);
      }
    } catch {
      setError(t.common.error);
    }
  };

  const handleDelete = (id: string) => setDeleteConfirm(id);

  const _confirmDelete = async () => {
    if (!deleteConfirm) return;
    try {
      const response = await fetch(`/api/v1/construction/procurements/${deleteConfirm}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) fetchItems();
    } finally {
      setDeleteConfirm(null);
    }
  };

  if (loading)
    return <div className="flex items-center justify-center h-64">{t.common.loading}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">{t.procurement.title}</h1>
        <button
          onClick={() => {
            setEditingItem(null);
            setFormData({ description: '', vendor: '', amount: '', status: 'draft' });
            setShowModal(true);
          }}
          className="btn-primary"
        >
          <span className="mr-2">+</span> {t.procurement.create}
        </button>
      </div>

      {error && <div className="alert-error">{error}</div>}

      <DataTable
        data={items}
        columns={[
          { key: 'description', header: t.procurement.description },
          { key: 'vendor', header: t.procurement.vendor },
          {
            key: 'amount',
            header: t.procurement.amount,
            render: (row: Procurement) => (
              <span className="font-mono">{formatCurrency(row.amount)}</span>
            ),
          },
          {
            key: 'status',
            header: t.procurement.status,
            render: (row: Procurement) => <StatusBadge status={row.status} t={t} />,
          },
        ]}
        onEdit={handleEdit}
        onDelete={handleDelete}
        t={t}
      />

      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={editingItem ? 'Edit Procurement' : 'Create Procurement'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description *</label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Vendor *</label>
            <input
              type="text"
              value={formData.vendor}
              onChange={(e) => setFormData({ ...formData, vendor: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Amount *</label>
            <input
              type="number"
              step="0.01"
              value={formData.amount}
              onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="draft">Draft</option>
              <option value="ordered">Ordered</option>
              <option value="received">Received</option>
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
        onConfirm={() => {
          if (deleteConfirm) {
            fetch(`/api/v1/construction/procurements/${deleteConfirm}`, {
              method: 'DELETE',
              headers: { Authorization: `Bearer ${token}` },
            }).then((r) => {
              if (r.ok) fetchItems();
            });
            setDeleteConfirm(null);
          }
        }}
        title="Confirm"
        message="Are you sure?"
      />
    </div>
  );
}

function StatusBadge({ status, t }: { status: string; t: TranslationKeys }) {
  const statusMap: Record<string, { label: string; class: string }> = {
    draft: { label: 'Draft', class: 'bg-gray-100 text-gray-800' },
    ordered: { label: t.procurement.ordered, class: 'bg-blue-100 text-blue-800' },
    received: { label: t.procurement.received, class: 'bg-green-100 text-green-800' },
  };
  const s = statusMap[status] || { label: status, class: 'bg-gray-100 text-gray-800' };
  return <span className={`px-2 py-1 text-xs font-medium rounded-full ${s.class}`}>{s.label}</span>;
}

function formatCurrency(value: string): string {
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  return new Intl.NumberFormat('ar-SA', { style: 'currency', currency: 'SAR' }).format(num);
}
