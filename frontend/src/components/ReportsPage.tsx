import React, { useState, useEffect } from 'react';
import { TranslationKeys } from '../i18n';

type ReportType =
  'financial' | 'profit_loss' | 'trial_balance' | 'account_balances' | 'projects' | 'claims';

interface ReportsPageProps {
  t: TranslationKeys;
  token: string;
}

export default function ReportsPage({ t, token }: ReportsPageProps) {
  const [reportType, setReportType] = useState<ReportType>('financial');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [data, setData] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [exportFormat, setExportFormat] = useState<'csv' | 'xlsx' | 'pdf'>('csv');

  const reportTypes = [
    { id: 'financial', label: t.reports.financialSummary, icon: '💰' },
    { id: 'profit_loss', label: t.reports.profitLoss, icon: '📊' },
    { id: 'trial_balance', label: t.reports.trialBalance, icon: '⚖️' },
    { id: 'account_balances', label: t.reports.accountBalances, icon: '📋' },
    { id: 'projects', label: t.projects.title, icon: '🏗️' },
    { id: 'claims', label: t.claims.title, icon: '📝' },
  ];

  const fetchReport = async () => {
    setLoading(true);
    try {
      let url = '';
      switch (reportType) {
        case 'financial':
          url = `/api/v1/reports/financial/summary?start_date=${dateRange.start}&end_date=${dateRange.end}`;
          break;
        case 'profit_loss':
          url = `/api/v1/reports/financial/profit-loss?format=json&start_date=${dateRange.start}&end_date=${dateRange.end}`;
          break;
        case 'trial_balance':
          url = `/api/v1/reports/financial/trial-balance?as_of_date=${dateRange.end}`;
          break;
        case 'account_balances':
          url = `/api/v1/reports/financial/account-balances`;
          break;
        case 'projects':
          url = `/api/v1/export/construction/projects?format=json`;
          break;
        case 'claims':
          url = `/api/v1/construction/claims`;
          break;
      }

      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setData(data);
      }
    } catch (err) {
      console.error('Report fetch failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!data) return;

    let url = '';
    switch (reportType) {
      case 'financial':
        url = `/api/v1/reports/financial/summary?format=${exportFormat}&start_date=${dateRange.start}&end_date=${dateRange.end}`;
        break;
      case 'profit_loss':
        url = `/api/v1/reports/financial/profit-loss?format=${exportFormat}&start_date=${dateRange.start}&end_date=${dateRange.end}`;
        break;
      case 'projects':
        url = `/api/v1/export/construction/projects?format=${exportFormat}`;
        break;
    }

    if (!url) return;

    try {
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const blob = await response.blob();
        const filename =
          response.headers.get('content-disposition')?.split('filename=')[1]?.replace(/"/g, '') ||
          `report.${exportFormat}`;
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  useEffect(() => {
    if (dateRange.start && dateRange.end) {
      fetchReport();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportType, dateRange]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">{t.reports.title}</h1>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t.reports.dateRange}
            </label>
            <div className="flex gap-2">
              <input
                type="date"
                value={dateRange.start}
                onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <span className="flex items-center text-gray-400">ـ</span>
              <input
                type="date"
                value={dateRange.end}
                onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Report Type</label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value as ReportType)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              {reportTypes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.icon} {r.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Export Format</label>
            <select
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value as 'csv' | 'xlsx' | 'pdf')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="csv">CSV</option>
              <option value="xlsx">Excel</option>
              <option value="pdf">PDF</option>
            </select>
          </div>
        </div>

        <div className="flex gap-4">
          <button
            onClick={fetchReport}
            disabled={loading || !dateRange.start || !dateRange.end}
            className="btn-primary"
          >
            {loading ? t.common.loading : 'Generate Report'}
          </button>
          <button onClick={handleExport} disabled={loading || !data} className="btn-secondary">
            {t.reports.export} {exportFormat.toUpperCase()}
          </button>
        </div>
      </div>

      {data ? (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-sm max-h-96">
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      ) : null}
    </div>
  );
}
