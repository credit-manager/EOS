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
  claim_date: string;
  period_start: string;
  period_end: string;
  total_amount: string;
  status: string;
}

interface ClaimsPageProps {
  t: TranslationKeys;
  token: string;
}

export default function ClaimsPage({ t, token }: ClaimsPageProps) {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [contracts, setContracts] = useState<
    { id: string; contract_number: string; title: string }[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingClaim, setEditingClaim] = useState<Claim | null>(null);
  const [formData, setFormData] = useState({
    claim_number: '',
    contract_id: '',
    claim_date: '',
    period_start: '',
    period_end: '',
    status: 'draft',
  });
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const contractName = (id: string) => {
    const c = contracts.find((x) => x.id === id);
    return c ? `${c.contract_number} - ${c.title}` : id;
  };

  const columns = [
    { key: 'claim_number', header: t.claims.claimNumber },
    {
      key: 'contract_name',
      header: t.contracts.projectName,
      render: (row: Claim) => <span>{contractName(row.contract_id)}</span>,
    },
    { key: 'claim_date', header: t.claims.date },
    { key: 'period_start', header: t.claims.period },
    {
      key: 'total_amount',
      header: t.claims.amount,
      render: (row: Claim) => <span className="font-mono">{formatCurrency(row.total_amount)}</span>,
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
        const items = data.items || data;
        setClaims(
          (Array.isArray(items) ? items : []).map((c: Record<string, unknown>) => ({
            id: String(c.id ?? ''),
            claim_number: String(c.claim_number ?? ''),
            contract_id: String(c.contract_id ?? ''),
            claim_date: String(c.claim_date ?? ''),
            period_start: String(c.period_start ?? ''),
            period_end: String(c.period_end ?? ''),
            total_amount: String(c.total_amount ?? '0'),
            status: String(c.status ?? 'draft'),
            contract_name: '',
          }))
        );
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
        const items = data.items || data;
        setContracts(
          (Array.isArray(items) ? items : []).map((c: Record<string, unknown>) => ({
            id: String(c.id ?? ''),
            contract_number: String(c.contract_number ?? ''),
            title: String(c.title ?? ''),
          }))
        );
      }
    } catch {
      // ignore
    }
  };

  const handleCreate = () => {
    setEditingClaim(null);
    setFormData({
      claim_number: '',
      contract_id: '',
      claim_date: '',
      period_start: '',
      period_end: '',
      status: 'draft',
    });
    setShowModal(true);
  };

  const handleEdit = (claim: Claim) => {
    setEditingClaim(claim);
    setFormData({
      claim_number: claim.claim_number,
      contract_id: claim.contract_id,
      claim_date: claim.claim_date,
      period_start: claim.period_start,
      period_end: claim.period_end,
      status: claim.status,
    });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingClaim
        ? `/api/v1/construction/claims/${editingClaim.id}`
        : '/api/v1/construction/claims';
      const method = editingClaim ? 'PATCH' : 'POST';
      const body = editingClaim
        ? { status: formData.status }
        : {
            contract_id: formData.contract_id,
            claim_number: formData.claim_number,
            claim_date: formData.claim_date,
            period_start: formData.period_start,
            period_end: formData.period_end,
          };

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
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
          {!editingClaim && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Claim Number *
                </label>
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
                      {c.contract_number} - {c.title}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-1 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Claim Date *
                  </label>
                  <input
                    type="date"
                    value={formData.claim_date}
                    onChange={(e) => setFormData({ ...formData, claim_date: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Period Start *
                  </label>
                  <input
                    type="date"
                    value={formData.period_start}
                    onChange={(e) => setFormData({ ...formData, period_start: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Period End *
                  </label>
                  <input
                    type="date"
                    value={formData.period_end}
                    onChange={(e) => setFormData({ ...formData, period_end: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
              </div>
            </>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              {editingClaim ? (
                <>
                  <option value="draft">{t.claims.draft}</option>
                  <option value="submitted">{t.claims.submitted}</option>
                  <option value="approved">{t.claims.approved}</option>
                  <option value="paid">{t.claims.paid}</option>
                </>
              ) : (
                <option value="draft">{t.claims.draft}</option>
              )}
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
    draft: { label: t.claims.draft, class: 'bg-gray-100 text-gray-800' },
    submitted: { label: t.claims.submitted, class: 'bg-yellow-100 text-yellow-800' },
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
