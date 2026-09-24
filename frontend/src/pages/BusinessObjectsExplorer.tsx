import { useState, useEffect } from 'react';
import { api } from '../api';
import { useI18n } from '../i18n';

interface EntityMeta {
  id: string;
  code: string;
  name: string;
  version: number;
  field_count: number;
  record_count?: number;
  status: string;
}

export function BusinessObjectsExplorer({
  token,
  onSelect,
}: {
  token: string;
  role: string;
  onSelect: (code: string) => void;
}) {
  const { t } = useI18n();
  const [entities, setEntities] = useState<EntityMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    api<EntityMeta[]>('/metadata/entities', token)
      .then((list) => {
        const rows = (Array.isArray(list) ? list : []).map((e) => ({
          id: String(e.id ?? ''),
          code: e.code,
          name: e.name ?? '',
          version: e.version ?? 1,
          field_count: e.field_count ?? 0,
          status: 'published',
        }));
        setEntities(rows);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [token]);

  const filtered = entities.filter((e) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return e.code.toLowerCase().includes(q) || (e.name || '').toLowerCase().includes(q);
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{t.businessObjectsExplorer.title}</h2>
          <p className="text-gray-500 mt-1">{entities.length} {t.businessObjectsExplorer.publishedEntities}</p>
        </div>
      </div>

      <div className="flex gap-3 items-center">
        <input
          type="text"
          placeholder={t.businessObjectsExplorer.searchPlaceholder}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 max-w-md px-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((entity) => (
          <button
            key={entity.code}
            onClick={() => onSelect(entity.code)}
            className="bg-white rounded-xl border border-gray-200 p-5 text-left hover:border-blue-300 hover:shadow-md transition-all group"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600 font-bold text-sm group-hover:bg-blue-100 transition-colors">
                {entity.code.slice(0, 2).toUpperCase()}
              </div>
              <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-green-100 text-green-700">
                {entity.status}
              </span>
            </div>
            <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
              {entity.code}
            </h3>
            {entity.name && <p className="text-sm text-gray-500 mt-0.5">{entity.name}</p>}
            <div className="flex gap-4 mt-3 text-xs text-gray-400">
              <span>{entity.field_count} {t.businessObjectsExplorer.fields}</span>
              <span>v{entity.version}</span>
            </div>
          </button>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12">
          <p className="text-4xl mb-3">📦</p>
          <p className="text-gray-500">{t.businessObjectsExplorer.noObjectsFound}</p>
          <p className="text-sm text-gray-400 mt-1">
            {t.businessObjectsExplorer.publishHint}
          </p>
        </div>
      )}
    </div>
  );
}
