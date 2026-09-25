import type { ReactNode } from 'react';
import { useI18n } from '../../i18n';

type AgentRow = { name: string; status: 'active' | 'idle'; load: number };

const AGENT_ROWS: AgentRow[] = [
  { name: 'Finance', status: 'active', load: 86 },
  { name: 'Operations', status: 'active', load: 72 },
  { name: 'Sales', status: 'active', load: 64 },
  { name: 'Procurement', status: 'idle', load: 18 },
  { name: 'Executive', status: 'active', load: 41 },
];

const REVENUE_BARS = [38, 44, 41, 52, 49, 58, 63, 60, 71, 76, 73, 88];
const EXPENSE_BARS = [26, 28, 30, 31, 33, 34, 36, 37, 38, 40, 41, 43];

function Sparkline({ points, tone }: { points: number[]; tone: 'blue' | 'emerald' | 'amber' }) {
  const stroke =
    tone === 'blue' ? '#3b82f6' : tone === 'emerald' ? '#10b981' : '#f59e0b';
  const w = 72;
  const h = 24;
  const max = Math.max(...points);
  const min = Math.min(...points);
  const range = max - min || 1;
  const path = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * w;
      const y = h - ((p - min) / range) * (h - 4) - 2;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden="true">
      <path d={path} fill="none" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function KpiCard({
  label,
  value,
  change,
  caption,
  tone,
  points,
}: {
  label: string;
  value: string;
  change?: string;
  caption: string;
  tone: 'blue' | 'emerald' | 'amber';
  points: number[];
}) {
  return (
    <div className="rounded-xl border border-white/8 bg-white/[0.03] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-wider text-slate-500">{label}</div>
          <div className="mt-2 text-2xl font-semibold tabular-nums tracking-tight text-white">{value}</div>
        </div>
        <Sparkline points={points} tone={tone} />
      </div>
      <div className="mt-2 flex items-center gap-2 text-xs">
        {change && (
          <span className="rounded-md bg-emerald-500/10 px-1.5 py-0.5 font-medium text-emerald-400">{change}</span>
        )}
        <span className="text-slate-500">{caption}</span>
      </div>
    </div>
  );
}

function BarChart() {
  const months = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];
  return (
    <div className="flex h-44 items-end gap-1.5 sm:gap-2">
      {months.map((month, i) => (
        <div key={`${month}-${i}`} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
          <div className="flex h-full w-full items-end justify-center gap-[3px]">
            <div
              className="w-1/2 rounded-t-sm bg-gradient-to-t from-blue-600 to-blue-400"
              style={{ height: `${REVENUE_BARS[i]}%` }}
            />
            <div
              className="w-1/2 rounded-t-sm bg-slate-600/70"
              style={{ height: `${EXPENSE_BARS[i]}%` }}
            />
          </div>
          <span className="text-[9px] text-slate-600">{month}</span>
        </div>
      ))}
    </div>
  );
}

function Panel({
  title,
  badge,
  children,
}: {
  title: string;
  badge?: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-white/8 bg-white/[0.03]">
      <div className="flex items-center justify-between border-b border-white/6 px-4 py-2.5">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{title}</span>
        {badge && (
          <span className="rounded-md bg-blue-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-blue-400">
            {badge}
          </span>
        )}
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

export default function CommandCenter() {
  const { t } = useI18n();

  const alerts = [
    { text: t.landing.dashPendingApproval, tone: 'amber' },
    { text: t.landing.dashLowStock, tone: 'blue' },
    { text: t.landing.dashOverdueInvoice, tone: 'red' },
  ] as const;

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 shadow-2xl shadow-slate-900/40">
      {/* Window chrome */}
      <div className="flex items-center gap-3 border-b border-white/8 bg-white/[0.02] px-4 py-3">
        <div className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-red-400/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-400/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/70" />
        </div>
        <div className="ms-2 hidden flex-1 items-center justify-center sm:flex">
          <span className="rounded-md border border-white/8 bg-white/5 px-4 py-1 text-[11px] text-slate-500">
            eos.app / command-center
          </span>
        </div>
        <span className="ms-auto flex items-center gap-1.5 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-semibold text-emerald-400">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
          {t.landing.dashActive}
        </span>
      </div>

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-5">
        <div>
          <h3 className="text-sm font-semibold text-white">{t.landing.dashTitle}</h3>
          <p className="mt-0.5 text-xs text-slate-500">{t.landing.dashMonthly}</p>
        </div>
        <div className="flex rounded-lg border border-white/8 bg-white/[0.03] p-0.5 text-[11px]">
          {['7d', '30d', '90d'].map((period) => (
            <span
              key={period}
              className={`rounded-md px-2.5 py-1 font-medium ${
                period === '30d' ? 'bg-blue-600 text-white' : 'text-slate-500'
              }`}
            >
              {period}
            </span>
          ))}
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-1 gap-3 px-4 pb-4 sm:grid-cols-2 sm:px-5 lg:grid-cols-4">
        <KpiCard
          label={t.landing.dashRevenue}
          value={t.landing.dashRevenueValue}
          change={t.landing.dashRevenueChange}
          caption={t.landing.dashMonthly}
          tone="blue"
          points={REVENUE_BARS}
        />
        <KpiCard
          label={t.landing.dashOperations}
          value={t.landing.dashOperationsValue}
          change={t.landing.dashOperationsChange}
          caption={t.landing.dashMonthly}
          tone="emerald"
          points={[40, 45, 43, 50, 55, 52, 60, 58, 65, 70, 68, 75]}
        />
        <KpiCard
          label={t.landing.dashCashFlow}
          value={t.landing.dashCashValue}
          change={t.landing.dashCashChange}
          caption={t.landing.dashMonthly}
          tone="emerald"
          points={[50, 48, 52, 55, 53, 58, 57, 62, 60, 65, 67, 70]}
        />
        <KpiCard
          label={t.landing.dashWorkforce}
          value={t.landing.dashWorkforceValue}
          caption={t.landing.dashAiAgents}
          tone="amber"
          points={[30, 34, 38, 36, 42, 48, 46, 52, 58, 62, 66, 72]}
        />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 gap-3 px-4 pb-5 sm:px-5 lg:grid-cols-3">
        {/* Chart */}
        <div className="rounded-xl border border-white/8 bg-white/[0.03] lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/6 px-4 py-2.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              {t.landing.dashFlowRevenue} vs {t.landing.dashFlowExpenses}
            </span>
            <div className="flex items-center gap-4 text-[10px] text-slate-500">
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-sm bg-blue-500" />
                {t.landing.dashFlowRevenue}
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-sm bg-slate-600" />
                {t.landing.dashFlowExpenses}
              </span>
            </div>
          </div>
          <div className="px-4 pt-4">
            <BarChart />
            <div className="mt-4 grid grid-cols-3 gap-3 border-t border-white/6 pt-3">
              {[
                { label: t.landing.dashFlowRevenue, value: t.landing.dashRevenueValue },
                { label: t.landing.dashFlowExpenses, value: '$1.55M' },
                { label: t.landing.dashFlowMargin, value: '35.4%' },
              ].map((item) => (
                <div key={item.label}>
                  <div className="text-[10px] uppercase tracking-wider text-slate-600">{item.label}</div>
                  <div className="mt-0.5 text-sm font-semibold tabular-nums text-slate-300">{item.value}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="px-4 pb-4 pt-3">
            <div className="flex items-center justify-between text-[11px] text-slate-500">
              <span>{t.landing.dashFlowMargin}: 35.4%</span>
              <span className="text-emerald-400">+2.1%</span>
            </div>
          </div>
        </div>

        {/* Right stack */}
        <div className="flex flex-col gap-3">
          <Panel title={t.landing.dashAiAgents} badge={`${t.landing.dashAgentsActive}`}>
            <div className="space-y-2.5">
              {AGENT_ROWS.map((agent) => (
                <div key={agent.name} className="flex items-center gap-3">
                  <span
                    className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                      agent.status === 'active' ? 'bg-emerald-400' : 'bg-slate-600'
                    }`}
                  />
                  <span className="flex-1 text-xs text-slate-300">{agent.name}</span>
                  <div className="h-1.5 w-16 overflow-hidden rounded-full bg-white/6">
                    <div
                      className={`h-full rounded-full ${
                        agent.status === 'active' ? 'bg-blue-500' : 'bg-slate-600'
                      }`}
                      style={{ width: `${agent.load}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-3 flex items-center gap-3 border-t border-white/6 pt-3 text-[11px] text-slate-500">
              <span className="text-emerald-400">{t.landing.dashAgentsActive}</span>
              <span>{t.landing.dashAgentsIdle}</span>
            </div>
          </Panel>

          <Panel title={t.landing.dashAutomation}>
            <div className="flex items-end justify-between">
              <div>
                <div className="text-2xl font-semibold tabular-nums text-white">
                  {t.landing.dashAutomationRuns}
                </div>
                <div className="mt-1 text-[11px] text-slate-500">{t.landing.dashAutomation}</div>
              </div>
              <div className="text-end">
                <div className="text-lg font-semibold tabular-nums text-emerald-400">
                  {t.landing.dashAutomationRate}
                </div>
                <div className="mt-1 text-[11px] text-slate-600">{t.landing.dashActive}</div>
              </div>
            </div>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/6">
              <div className="h-full w-[94%] rounded-full bg-gradient-to-r from-blue-600 to-emerald-400" />
            </div>
          </Panel>

          <Panel title={t.landing.dashAlerts} badge={t.landing.dashAlertsCount}>
            <ul className="space-y-2">
              {alerts.map((alert) => (
                <li key={alert.text} className="flex items-start gap-2 text-[11px] leading-relaxed">
                  <span
                    className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${
                      alert.tone === 'amber'
                        ? 'bg-amber-400'
                        : alert.tone === 'red'
                        ? 'bg-red-400'
                        : 'bg-blue-400'
                    }`}
                  />
                  <span className="text-slate-400">{alert.text}</span>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title={t.landing.dashBusinessHealth}>
            <div className="flex items-center gap-4">
              <div className="relative h-16 w-16 shrink-0">
                <svg viewBox="0 0 36 36" className="h-16 w-16 -rotate-90">
                  <circle cx="18" cy="18" r="15.9" fill="none" stroke="#1e293b" strokeWidth="3" />
                  <circle
                    cx="18"
                    cy="18"
                    r="15.9"
                    fill="none"
                    stroke="#3b82f6"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeDasharray="92 100"
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-sm font-semibold tabular-nums text-white">
                  {t.landing.dashHealthScore}
                </span>
              </div>
              <div className="text-xs text-slate-500">
                <div className="font-medium text-slate-300">{t.landing.dashHealthLabel}</div>
                <div className="mt-1">{t.landing.dashAlertsLabel}: {t.landing.dashAlertsCount}</div>
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
