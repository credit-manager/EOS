import React, { useState, useEffect } from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';
import StatusBadge from '../components/StatusBadge';
import { getPlans, type Plan } from '../adminApi';

export default function SubscriptionPlans() {
  const { isRTL: _isRTL, t } = useI18n();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('2to_eos_access_token');
    if (!token) return;
    setLoading(true);
    getPlans(token).then((res) => {
      setPlans(Array.isArray(res) ? res : []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const c = t.master.common;
  const parseFeatures = (features: Record<string, boolean> | null): string[] => {
    if (!features) return [];
    return Object.entries(features).filter(([, v]) => v).map(([k]) => k);
  };

  return (
    <AdminPage title={t.master.plans.title} subtitle={t.master.plans.features}>
      <div className="flex justify-between mb-6">
        <div className="flex gap-2">
          {[c.all, c.active, 'Archived'].map((tab) => (
            <button key={tab} className="px-4 py-2 rounded-lg text-sm bg-gray-100 text-gray-600 hover:bg-gray-200">{tab}</button>
          ))}
        </div>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">+ {t.master.plans.actions.createPlan}</button>
      </div>
      {loading ? (
        <div className="text-center py-12 text-gray-500">{c.loading}</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map((plan) => (
            <div key={plan.id} className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-gray-900">{plan.name}</h3>
                <StatusBadge status={plan.isActive ? 'active' : 'inactive'} />
              </div>
              <p className="text-3xl font-bold text-gray-900 mb-4">${plan.priceMonthly}/mo</p>
              <div className="space-y-2 mb-6">
                {parseFeatures(plan.features).map((f, j) => (
                  <div key={j} className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="text-green-500">✓</span> {f}
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-3 gap-2 text-center text-xs text-gray-500 mb-4 border-t border-gray-100 pt-4">
                <div><p className="font-medium">{plan.maxUsers}</p><p>{t.master.users.title}</p></div>
                <div><p className="font-medium">{plan.maxStorageGb}GB</p><p>{t.master.tenants.storage}</p></div>
                <div><p className="font-medium">{plan.code}</p><p>Code</p></div>
              </div>
              <div className="flex gap-2">
                <button className="flex-1 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">{c.edit}</button>
                <button className="flex-1 px-3 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200">{t.master.plans.actions.duplicatePlan}</button>
              </div>
            </div>
          ))}
          {plans.length === 0 && (
            <div className="col-span-3 text-center py-12 text-gray-500">{c.noData}</div>
          )}
        </div>
      )}
    </AdminPage>
  );
}
