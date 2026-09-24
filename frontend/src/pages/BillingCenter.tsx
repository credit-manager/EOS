import React, { useState, useEffect } from 'react';
import { useI18n } from '../i18n';
import AdminPage from '../components/AdminPage';
import StatCard from '../components/StatCard';
import StatusBadge from '../components/StatusBadge';
import { getBillingKPIs, getInvoices, type BillingKPIs, type Invoice } from '../adminApi';

export default function BillingCenter() {
  const { isRTL: _isRTL, t } = useI18n();
  const [kpis, setKpis] = useState<BillingKPIs | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('2to_eos_access_token');
    if (!token) return;
    setLoading(true);
    Promise.all([
      getBillingKPIs(token).catch(() => null),
      getInvoices(token).catch(() => ({ invoices: [] })),
    ]).then(([kpiRes, invRes]) => {
      if (kpiRes) setKpis(kpiRes);
      setInvoices(invRes?.invoices || []);
    }).finally(() => setLoading(false));
  }, []);

  const c = t.master.common;
  const kpiCards = kpis ? [
    { title: t.master.billing.mrr, value: `$${kpis.mrr.toLocaleString()}`, icon: '📈', color: 'green' },
    { title: t.master.billing.arr, value: `$${(kpis.arr / 1000).toFixed(0)}K`, icon: '📊', color: 'blue' },
    { title: t.master.billing.revenue, value: `$${(kpis.totalRevenue / 1000).toFixed(0)}K`, icon: '💵', color: 'purple' },
    { title: t.master.billing.failedPayments, value: `$${kpis.outstanding.toLocaleString()}`, icon: '⚠️', color: 'orange' },
  ] : [
    { title: t.master.billing.mrr, value: '-', icon: '📈', color: 'green' },
    { title: t.master.billing.arr, value: '-', icon: '📊', color: 'blue' },
    { title: t.master.billing.revenue, value: '-', icon: '💵', color: 'purple' },
    { title: t.master.billing.failedPayments, value: '-', icon: '⚠️', color: 'orange' },
  ];

  return (
    <AdminPage title={t.master.billing.title} subtitle={t.master.billing.revenue}>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {kpiCards.map((kpi, i) => <StatCard key={i} {...kpi} changeType="up" />)}
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{t.master.billing.invoices}</h3>
        {loading ? (
          <div className="text-center py-8 text-gray-500">{c.loading}</div>
        ) : (
          <table className="min-w-full text-sm">
            <thead><tr className="border-b border-gray-200">
              <th className="text-left p-3">Invoice</th>
              <th className="text-left p-3">{t.master.users.tenant}</th>
              <th className="text-left p-3">{t.master.billing.revenue}</th>
              <th className="text-left p-3">{t.master.tenants.status}</th>
              <th className="text-left p-3">{c.createdAt}</th>
            </tr></thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id} className="border-t border-gray-100">
                  <td className="p-3 font-mono text-xs">{inv.id.slice(0, 8)}</td>
                  <td className="p-3 font-mono text-xs">{inv.tenantId.slice(0, 8)}</td>
                  <td className="p-3">${inv.amount.toLocaleString()} {inv.currency}</td>
                  <td className="p-3"><StatusBadge status={inv.status} /></td>
                  <td className="p-3">{inv.createdAt ? new Date(inv.createdAt).toLocaleDateString() : '-'}</td>
                </tr>
              ))}
              {invoices.length === 0 && (
                <tr><td colSpan={5} className="p-6 text-center text-gray-500">{c.noData}</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </AdminPage>
  );
}
