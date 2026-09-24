import React, { useState, useEffect } from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';
import StatusBadge from '../components/StatusBadge';
import { getFeatureFlags, updateFeatureFlag, type FeatureFlag } from '../adminApi';

export default function FeatureFlags() {
  const { isRTL: _isRTL, t } = useI18n();
  const [features, setFeatures] = useState<FeatureFlag[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('2to_eos_access_token');
    if (!token) return;
    setLoading(true);
    getFeatureFlags(token).then((res) => {
      setFeatures(res.flags || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const c = t.master.common;

  const toggleFlag = async (id: string, isActive: boolean) => {
    const token = localStorage.getItem('2to_eos_access_token');
    if (!token) return;
    try {
      await updateFeatureFlag(token, id, { isActive: !isActive });
      setFeatures((prev) => prev.map((f) => f.id === id ? { ...f, isActive: !isActive } : f));
    } catch {}
  };

  return (
    <AdminPage title={t.master.featureFlags.title} subtitle={t.master.featureFlags.global}>
      <div className="flex justify-between mb-6">
        <div className="flex gap-2">
          {[c.all, t.master.featureFlags.global, t.master.featureFlags.byPlan, t.master.featureFlags.byTenant].map((filter) => (
            <button key={filter} className="px-3 py-1.5 rounded-lg text-sm bg-gray-100 text-gray-600 hover:bg-gray-200">{filter}</button>
          ))}
        </div>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm">+ {c.new} Feature</button>
      </div>
      {loading ? (
        <div className="text-center py-12 text-gray-500">{c.loading}</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="min-w-full">
            <thead className="bg-gray-50"><tr>
              <th className="text-left p-3 text-xs font-semibold text-gray-600">Feature</th>
              <th className="text-left p-3 text-xs font-semibold text-gray-600">{t.master.featureFlags.global}</th>
              <th className="text-left p-3 text-xs font-semibold text-gray-600">{t.master.featureFlags.byPlan}</th>
              <th className="text-left p-3 text-xs font-semibold text-gray-600">{t.master.users.status}</th>
              <th className="text-left p-3 text-xs font-semibold text-gray-600">{c.actions}</th>
            </tr></thead>
            <tbody>
              {features.map((f) => (
                <tr key={f.id} className="border-t border-gray-100">
                  <td className="p-3">
                    <p className="font-medium">{f.name}</p>
                    <p className="text-xs text-gray-500">{f.description}</p>
                  </td>
                  <td className="p-3">{f.isGlobal ? '✅' : '❌'}</td>
                  <td className="p-3"><div className="flex gap-1">{f.enabledPlans.map((p, j) => <span key={j} className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">{p}</span>)}</div></td>
                  <td className="p-3"><StatusBadge status={f.isActive ? 'active' : 'inactive'} /></td>
                  <td className="p-3">
                    <div className="flex gap-2">
                      <button className="text-green-600 text-sm hover:underline" onClick={() => toggleFlag(f.id, f.isActive)}>{c.enable}</button>
                      <button className="text-red-600 text-sm hover:underline" onClick={() => toggleFlag(f.id, f.isActive)}>{c.disable}</button>
                      <button className="text-blue-600 text-sm hover:underline">{c.edit}</button>
                    </div>
                  </td>
                </tr>
              ))}
              {features.length === 0 && (
                <tr><td colSpan={5} className="p-6 text-center text-gray-500">{c.noData}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </AdminPage>
  );
}
