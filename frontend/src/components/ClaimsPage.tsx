import React, { useState, useEffect } from 'react';
import { TranslationKeys } from '../i18n';
import DataTable from './DataTable';
import Modal from './Modal';
import ConfirmDialog from './ConfirmDialog';

interface Claim {
  id: string;
  claim_number: string;
  contract_id: string;
  contract_name: string;
  amount: string;
  status: string;
}

interface ClaimsPageProps {
  t: TranslationKeys;
  token: string;
}

export default function ClaimsPage({ t, token }: ClaimsPageProps) {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [contracts, setContracts] = useState<
    { id: string; number: string; project_name: string }[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingClaim, setEditingClaim] = useState<Claim | null>(null);
  const [formData, setFormData] = useState({
    claim_number: '',
    contract_id: '',
    amount: '',
    status: 'pending',
  });
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const columns = [
    { key: 'claim_number', header: t.claims.claimNumber },
    { key: 'contract_name', header: t.contracts.projectName },
    {
      key: 'amount',
      header: t.claims.amount,
      render: (row: Claim) => <span className="font-mono">{formatCurrency(row.amount)}</span>,
    },
    {
      key: 'status',
      header: t.claims.status,
      render: (row: Claim) => <StatusBadge status={row.status} t={t} />,
    },
  ];

  useEffect(() => {
    fetchClaims();
    fetchContracts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchClaims = async () => {
    try {
      const response = await fetch('/api/v1/construction/claims', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setClaims(data.items || data);
      }
    } catch {
      setError(t.common.error);
    } finally {
      setLoading(false);
    }
  };

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
      // ignore
    }
  };

  const handleCreate = () => {
    setEditingClaim(null);
    setFormData({ claim_number: '', contract_id: '', amount: '', status: 'pending' });
    setShowModal(true);
  };

  const handleEdit = (claim: Claim) => {
    setEditingClaim(claim);
    setFormData({ ...claim });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingClaim
        ? `/api/v1/construction/claims/${editingClaim.id}`
        : '/api/v1/construction/claims';
      const method = editingClaim ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setShowModal(false);
        fetchClaims();
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
      const response = await fetch(`/api/v1/construction/claims/${deleteConfirm}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) fetchClaims();
    } finally {
      setDeleteConfirm(null);
    }
  };

  if (loading)
    return <div className="flex items-center justify-center h-64">{t.common.loading}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">{t.claims.title}</h1>
        <button onClick={handleCreate} className="btn-primary">
          <span className="mr-2">+</span> {t.claims.create}
        </button>
      </div>

      {error && <div className="alert-error">{error}</div>}

      <DataTable
        data={claims}
        columns={columns}
        onEdit={handleEdit}
        onDelete={handleDelete}
        t={t}
      />

      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={editingClaim ? 'Edit Claim' : 'Create Claim'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Claim Number *</label>
            <input
              type="text"
              value={formData.claim_number}
              onChange={(e) => setFormData({ ...formData, claim_number: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Contract *</label>
            <select
              value={formData.contract_id}
              onChange={(e) => setFormData({ ...formData, contract_id: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="">Select Contract</option>
              {contracts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.number} - {c.project_name}
                </option>
              ))}
            </select>
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
              <option value="pending">{t.claims.pending}</option>
              <option value="approved">{t.claims.approved}</option>
              <option value="rejected">{t.claims.rejected}</option>
              <option value="paid">{t.claims.paid}</option>
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
    pending: { label: t.claims.pending, class: 'bg-yellow-100 text-yellow-800' },
    approved: { label: t.claims.approved, class: 'bg-green-100 text-green-800' },
    rejected: { label: t.claims.rejected, class: 'bg-red-100 text-red-800' },
    paid: { label: t.claims.paid, class: 'bg-blue-100 text-blue-800' },
  };
  const s = statusMap[status] || { label: status, class: 'bg-gray-100 text-gray-800' };
  return <span className={`px-2 py-1 text-xs font-medium rounded-full ${s.class}`}>{s.label}</span>;
}

function formatCurrency(value: string): string {
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  return new Intl.NumberFormat('ar-SA', { style: 'currency', currency: 'SAR' }).format(num);
}
