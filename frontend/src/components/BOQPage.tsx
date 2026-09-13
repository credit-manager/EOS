import React, { useState, useEffect } from 'react';
import { TranslationKeys } from '../i18n';
import DataTable from './DataTable';
import Modal from './Modal';
import ConfirmDialog from './ConfirmDialog';

interface BOQ {
  id: string;
  contract_id: string;
  contract_name: string;
  status: string;
  items_count: number;
  total_amount: string;
}

interface BOQPageProps {
  t: TranslationKeys;
  token: string;
}

export default function BOQPage({ t, token }: BOQPageProps) {
  const [boqs, setBoqs] = useState<BOQ[]>([]);
  const [contracts, setContracts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingBOQ, setEditingBOQ] = useState<BOQ | null>(null);
  const [formData, setFormData] = useState({
    contract_id: '',
    status: 'draft',
  });
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const columns = [
    { key: 'contract_name', header: 'Contract' },
    { key: 'status', header: 'Status', render: (row: BOQ) => <StatusBadge status={row.status} /> },
    { key: 'items_count', header: 'Items', className: 'text-right' },
    { key: 'total_amount', header: 'Total', render: (row: BOQ) => <span className="font-mono">{formatCurrency(row.total_amount)}</span> },
  ];

  useEffect(() => {
    fetchBOQs();
    fetchContracts();
  }, []);

  const fetchBOQs = async () => {
    try {
      const response = await fetch('/api/v1/construction/boqs', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setBoqs(data.items || data);
      }
    } catch (err) {
      setError('Failed to load BOQs');
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
    } catch (err) {
      // ignore
    }
  };

  const handleCreate = () => {
    setEditingBOQ(null);
    setFormData({ contract_id: '', status: 'draft' });
    setShowModal(true);
  };

  const handleEdit = (boq: BOQ) => {
    setEditingBOQ(boq);
    setFormData({ contract_id: boq.contract_id, status: boq.status });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingBOQ
        ? `/api/v1/construction/boqs/${editingBOQ.id}`
        : '/api/v1/construction/boqs';
      const method = editingBOQ ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(formData),
      });
      
      if (response.ok) {
        setShowModal(false);
        fetchBOQs();
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to save');
      }
    } catch (err) {
      setError('Failed to save');
    }
  };

  const handleDelete = (id: string) => setDeleteConfirm(id);
  
  const confirmDelete = async () => {
    if (!deleteConfirm) return;
    try {
      const response = await fetch(`/api/v1/construction/boqs/${deleteConfirm}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) fetchBOQs();
    } finally {
      setDeleteConfirm(null);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64">Loading...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Bill of Quantities</h1>
        <button onClick={handleCreate} className="btn-primary">
          <span className="mr-2">+</span> Create BOQ
        </button>
      </div>

      {error && <div className="alert-error">{error}</div>}

      <DataTable
        data={boqs}
        columns={columns}
        onEdit={handleEdit}
        onDelete={handleDelete}
        t={{} as any}
      />

      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title={editingBOQ ? 'Edit BOQ' : 'Create BOQ'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Contract *</label>
            <select
              value={formData.contract_id}
              onChange={(e) => setFormData({ ...formData, contract_id: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="">Select Contract</option>
              {contracts.map((c: any) => (
                <option key={c.id} value={c.id}>{c.number} - {c.project_name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="draft">Draft</option>
              <option value="submitted">Submitted</option>
              <option value="approved">Approved</option>
            </select>
          </div>
          <div className="flex justify-end gap-3 pt-4">
            <button type="button" onClick={() => setShowModal(false)} className="btn-secondary">Cancel</button>
            <button type="submit" className="btn-primary">Save</button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog isOpen={!!deleteConfirm} onClose={() => setDeleteConfirm(null)} onConfirm={() => { if(deleteConfirm) { fetch(`/api/v1/construction/boqs/${deleteConfirm}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } }).then(r => { if (r.ok) fetchBOQs(); }); setDeleteConfirm(null); }} } title="Confirm" message="Are you sure?" />
    </div>
  );
}

const columns = [
  { key: 'contract_name', header: 'Contract' },
  { key: 'status', header: 'Status', render: (row: any) => <StatusBadge status={row.status} /> },
  { key: 'items_count', header: 'Items', className: 'text-right' },
  { key: 'total_amount', header: 'Total', render: (row: any) => <span className="font-mono">{formatCurrency(row.total_amount)}</span> },
];

function StatusBadge({ status }: { status: string }) {
  const statusMap: Record<string, { label: string; class: string }> = {
    draft: { label: 'Draft', class: 'bg-gray-100 text-gray-800' },
    submitted: { label: 'Submitted', class: 'bg-yellow-100 text-yellow-800' },
    approved: { label: 'Approved', class: 'bg-green-100 text-green-800' },
  };
  const s = statusMap[status] || { label: status, class: 'bg-gray-100 text-gray-800' };
  return <span className={`px-2 py-1 text-xs font-medium rounded-full ${s.class}`}>{s.label}</span>;
}

function formatCurrency(value: string): string {
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  return new Intl.NumberFormat('ar-SA', { style: 'currency', currency: 'SAR' }).format(num);
}