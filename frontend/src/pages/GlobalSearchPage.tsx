import React from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';

export default function GlobalSearchPage() {
  const { isRTL: _isRTL, t } = useI18n();
  const results = [
    { type: 'tenant', name: 'Acme Corp', id: 'T-001', icon: '🏢' },
    { type: 'user', name: 'admin@acme.com', id: 'U-001', icon: '👤' },
    { type: 'invoice', name: 'INV-2026-001', id: 'I-001', icon: '📄' },
    { type: 'api_key', name: 'key_001', id: 'K-001', icon: '🔑' },
  ];

  return (
    <AdminPage title={t.globalSearch.title} subtitle={t.globalSearch.subtitle}>
      <input type="text" placeholder={t.globalSearch.searchPlaceholder} className="w-full px-4 py-3 border border-gray-300 rounded-xl text-lg mb-6 focus:ring-2 focus:ring-blue-500" />
      <div className="space-y-3">
        {results.map((r, i) => (
          <div key={i} className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-4 cursor-pointer hover:bg-gray-50">
            <span className="text-2xl">{r.icon}</span>
            <div className="flex-1"><p className="font-medium text-gray-900">{r.name}</p><p className="text-xs text-gray-500">{r.id} · {r.type}</p></div>
            <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
          </div>
        ))}
      </div>
    </AdminPage>
  );
}
