import React, { useState, useEffect } from 'react';
import { TranslationKeys } from '../i18n';
import DataTable from './DataTable';
import Modal from './Modal';
import ConfirmDialog from './ConfirmDialog';

interface Account {
  id: string;
  code: string;
  name: string;
  account_type: string;
}

interface JournalEntry {
  id: string;
  entry_date: string;
  description: string;
  reference: string;
}

type FinancialRow = Account | JournalEntry;

interface ColumnDef {
  key: string;
  header: string;
  className?: string;
  render?: (row: FinancialRow) => React.ReactNode;
}

interface FinancialPageProps {
  t: TranslationKeys;
  token: string;
}

export default function FinancialPage({ t, token }: FinancialPageProps) {
  const [activeTab, setActiveTab] = useState<'accounts' | 'entries'>('accounts');
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    account_type: 'asset',
  });
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const accountColumns: ColumnDef[] = [
    { key: 'code', header: t.financial.accountType, className: 'font-mono' },
    { key: 'name', header: t.financial.accountType },
    {
      key: 'account_type',
      header: t.financial.accountType,
      render: (row: FinancialRow) => {
        const acc = row as Account;
        return <TypeBadge type={acc.account_type} t={t} />;
      },
    },
  ];

  const entryColumns: ColumnDef[] = [
    {
      key: 'entry_date',
      header: t.financial.accountType,
      render: (row: FinancialRow) => formatDate((row as JournalEntry).entry_date),
    },
    { key: 'description', header: t.financial.accountType },
    { key: 'reference', header: t.financial.accountType, className: 'font-mono' },
  ];

  useEffect(() => {
    fetchAccounts();
    fetchEntries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchAccounts = async () => {
    try {
      const response = await fetch('/api/v1/financial/accounts', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setAccounts(data.items || data);
      }
    } catch {
      setError(t.common.error);
    } finally {
      setLoading(false);
    }
  };

  const fetchEntries = async () => {
    try {
      const response = await fetch('/api/v1/financial/entries', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setEntries(data.items || data);
      }
    } catch {
      // ignore
    }
  };

  const handleCreate = () => {
    setEditingAccount(null);
    setFormData({ code: '', name: '', account_type: 'asset' });
    setShowModal(true);
  };

  const handleEdit = (account: Account) => {
    setEditingAccount(account);
    setFormData({ ...account });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingAccount
        ? `/api/v1/financial/accounts/${editingAccount.id}`
        : '/api/v1/financial/accounts';
      const method = editingAccount ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setShowModal(false);
        fetchAccounts();
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
      const response = await fetch(`/api/v1/financial/accounts/${deleteConfirm}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) fetchAccounts();
    } finally {
      setDeleteConfirm(null);
    }
  };

  if (loading)
    return <div className="flex items-center justify-center h-64">{t.common.loading}</div>;

  const currentData = activeTab === 'accounts' ? accounts : entries;
  const currentColumns = activeTab === 'accounts' ? accountColumns : entryColumns;
  const currentTitle = activeTab === 'accounts' ? t.financial.accounts : t.financial.journalEntries;
  const _currentCreateLabel =
    activeTab === 'accounts' ? t.financial.accounts : t.financial.createEntry;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex gap-4 border-b border-gray-200 pb-2">
          {['accounts', 'entries'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as 'accounts' | 'entries')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab === 'accounts' ? t.financial.accounts : t.financial.journalEntries}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-gray-900">{currentTitle}</h1>
          <button onClick={handleCreate} className="btn-primary">
            <span className="mr-2">+</span> {t.common.create}
          </button>
        </div>
      </div>

      {error && <div className="alert-error">{error}</div>}

      <DataTable
        data={currentData as FinancialRow[]}
        columns={currentColumns}
        onEdit={handleEdit as (row: FinancialRow) => void}
        onDelete={handleDelete}
        t={t}
      />

      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={editingAccount ? 'Edit Account' : 'Create Account'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Code *</label>
            <input
              type="text"
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Account Type *</label>
            <select
              value={formData.account_type}
              onChange={(e) => setFormData({ ...formData, account_type: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="asset">{t.financial.asset}</option>
              <option value="liability">{t.financial.liability}</option>
              <option value="equity">{t.financial.equity}</option>
              <option value="revenue">{t.financial.revenue}</option>
              <option value="expense">{t.financial.expense}</option>
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
            fetch(`/api/v1/financial/accounts/${deleteConfirm}`, {
              method: 'DELETE',
              headers: { Authorization: `Bearer ${token}` },
            }).then((r) => {
              if (r.ok) fetchAccounts();
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

function TypeBadge({ type, t }: { type: string; t: TranslationKeys }) {
  const typeMap: Record<string, { label: string; class: string }> = {
    asset: { label: t.financial.asset, class: 'bg-blue-100 text-blue-800' },
    liability: { label: t.financial.liability, class: 'bg-red-100 text-red-800' },
    equity: { label: t.financial.equity, class: 'bg-purple-100 text-purple-800' },
    revenue: { label: t.financial.revenue, class: 'bg-green-100 text-green-800' },
    expense: { label: t.financial.expense, class: 'bg-yellow-100 text-yellow-800' },
  };
  const s = typeMap[type] || { label: type, class: 'bg-gray-100 text-gray-800' };
  return <span className={`px-2 py-1 text-xs font-medium rounded-full ${s.class}`}>{s.label}</span>;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('ar-SA');
}
