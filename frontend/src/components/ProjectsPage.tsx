import React, { useState, useEffect } from 'react';
import { TranslationKeys } from '../i18n';
import DataTable from './DataTable';
import Modal from './Modal';
import ConfirmDialog from './ConfirmDialog';

interface Project {
  id: string;
  code: string;
  name: string;
  status: string;
  budget: string;
  client_name: string;
  location: string;
}

interface ProjectsPageProps {
  t: TranslationKeys;
  token: string;
}

export default function ProjectsPage({ t, token }: ProjectsPageProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    status: 'planning',
    budget: '',
    client_name: '',
    location: '',
  });
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const columns = [
    { key: 'code', header: t.projects.code, className: 'font-mono' },
    { key: 'name', header: t.projects.name },
    {
      key: 'status',
      header: t.projects.status,
      render: (row: Project) => <StatusBadge status={row.status} t={t} />,
    },
    {
      key: 'budget',
      header: t.projects.budget,
      render: (row: Project) => <span className="font-mono">{formatCurrency(row.budget)}</span>,
    },
    { key: 'client_name', header: t.projects.client },
    { key: 'location', header: t.projects.location },
  ];

  useEffect(() => {
    fetchProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
      setError(t.common.error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    setEditingProject(null);
    setFormData({
      code: '',
      name: '',
      status: 'planning',
      budget: '',
      client_name: '',
      location: '',
    });
    setShowModal(true);
  };

  const handleEdit = (project: Project) => {
    setEditingProject(project);
    setFormData({ ...project });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingProject
        ? `/api/v1/construction/projects/${editingProject.id}`
        : '/api/v1/construction/projects';
      const method = editingProject ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setShowModal(false);
        fetchProjects();
      } else {
        const data = await response.json();
        setError(data.detail || t.common.error);
      }
    } catch {
      setError(t.common.error);
    }
  };

  const handleDelete = (id: string) => {
    setDeleteConfirm(id);
  };

  const confirmDelete = async () => {
    if (!deleteConfirm) return;
    try {
      const response = await fetch(`/api/v1/construction/projects/${deleteConfirm}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        fetchProjects();
      }
    } catch {
      setError(t.common.error);
    } finally {
      setDeleteConfirm(null);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64">{t.common.loading}</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">{t.projects.title}</h1>
        <button onClick={handleCreate} className="btn-primary">
          <span className="mr-2">+</span> {t.projects.create}
        </button>
      </div>

      {error && <div className="alert-error">{error}</div>}

      <DataTable
        data={projects}
        columns={columns}
        onEdit={handleEdit}
        onDelete={handleDelete}
        t={t}
      />

      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={editingProject ? t.projects.edit : t.projects.create}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t.projects.code} *
            </label>
            <input
              type="text"
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t.projects.name} *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t.projects.status}
            </label>
            <select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="planning">{t.projects.planning}</option>
              <option value="active">{t.projects.active}</option>
              <option value="completed">{t.projects.completed}</option>
              <option value="on_hold">{t.projects.onHold}</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t.projects.budget}
            </label>
            <input
              type="number"
              step="0.01"
              value={formData.budget}
              onChange={(e) => setFormData({ ...formData, budget: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t.projects.client}
            </label>
            <input
              type="text"
              value={formData.client_name}
              onChange={(e) => setFormData({ ...formData, client_name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t.projects.location}
            </label>
            <input
              type="text"
              value={formData.location}
              onChange={(e) => setFormData({ ...formData, location: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
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
    planning: { label: t.projects.planning, class: 'bg-yellow-100 text-yellow-800' },
    active: { label: t.projects.active, class: 'bg-green-100 text-green-800' },
    completed: { label: t.projects.completed, class: 'bg-blue-100 text-blue-800' },
    on_hold: { label: t.projects.onHold, class: 'bg-gray-100 text-gray-800' },
  };
  const s = statusMap[status] || { label: status, class: 'bg-gray-100 text-gray-800' };
  return <span className={`px-2 py-1 text-xs font-medium rounded-full ${s.class}`}>{s.label}</span>;
}

function formatCurrency(value: string): string {
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  return new Intl.NumberFormat('ar-SA', { style: 'currency', currency: 'SAR' }).format(num);
}
