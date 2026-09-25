"use client";

import { useCallback, useEffect, useState } from "react";
import { useI18n } from '../i18n';

interface User {
  user_id: string;
  email: string;
  tenant_id: string;
  role: string;
}

interface TaskItem {
  id: string;
  title: string;
  type: "approval" | "action" | "reminder";
  priority: "high" | "medium" | "low";
  status: "pending" | "in_progress" | "done";
  due?: string;
}

interface KPICard {
  label: string;
  value: string;
  icon: string;
  trend?: string;
  color: string;
}

interface AlertItem {
  id: string;
  type: "info" | "warning" | "error";
  title: string;
  message: string;
  time: string;
}

interface DashboardSummary {
  total_budget: string;
  active_projects: number;
  pending_approvals: number;
  kpi_projects: KPICard[];
  kpi_financial: KPICard[];
}

export default function Workspace({
  token,
  user: _user,
}: {
  token: string;
  user?: User;
}) {
  const { t } = useI18n();
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [askQuery, setAskQuery] = useState("");
  const [askResponse, setAskResponse] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);

  const fetchDashboard = useCallback(async () => {
    try {
      const h = { Authorization: `Bearer ${token}` };

      const [tasksRes, summaryRes, alertsRes] = await Promise.all([
        fetch("/api/v1/workflows/my-tasks", { headers: h }),
        fetch("/api/v1/construction/pack/dashboards/project-health", { headers: h }),
        fetch("/api/v1/notifications/alerts", { headers: h }),
      ]);

      if (tasksRes.ok) {
        const body = await tasksRes.json();
        setTasks(
          Array.isArray(body)
            ? body
            : body?.items || body?.tasks || []
        );
      }

      if (summaryRes.ok) {
        const body = await summaryRes.json();
        setSummary({
          total_budget: body?.total_budget || "0 EGP",
          active_projects: body?.active_projects || body?.projects?.length || 0,
          pending_approvals: body?.pending_approvals || 0,
          kpi_projects: (body?.kpi_projects || []).map((k: KPICard) => ({
            label: k.label,
            value: k.value,
            icon: k.icon,
            trend: k.trend,
            color: k.color,
          })),
          kpi_financial: (body?.kpi_financial || []).map((k: KPICard) => ({
            label: k.label,
            value: k.value,
            icon: k.icon,
            trend: k.trend,
            color: k.color,
          })),
        });
      }

      if (alertsRes.ok) {
        const body = await alertsRes.json();
        setAlerts(Array.isArray(body) ? body : body?.alerts || []);
      }
    } catch {
      // keep last known state
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchDashboard();
    const id = setInterval(fetchDashboard, 30000);
    return () => clearInterval(id);
  }, [token, fetchDashboard]);

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!askQuery.trim()) return;
    setAsking(true);
    try {
      const r = await fetch("/api/v1/ai/ask", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ query: askQuery }),
      });
      const data = await r.json();
      setAskResponse(data?.answer || data?.response || JSON.stringify(data));
    } catch {
      setAskResponse(t.workspacePage.aiConnectionError);
    } finally {
      setAsking(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        <span className="ml-3 text-gray-500">{t.workspacePage.loadingDashboard}</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{t.workspacePage.unifiedDashboard}</h1>
        <p className="text-gray-500 text-sm mt-1">
          {t.workspacePage.dashboardSubtitle}
        </p>
      </div>

      {/* Ask EOS bar */}
      <form
        onSubmit={handleAsk}
        className="flex gap-3 bg-blue-50 border border-blue-100 rounded-xl px-4 py-3"
      >
        <input
          type="text"
          value={askQuery}
          onChange={(e) => setAskQuery(e.target.value)}
          placeholder={t.workspacePage.askPlaceholder}
          className="flex-1 bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
        />
        <button
          type="submit"
          disabled={asking || !askQuery.trim()}
          className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {asking ? t.workspacePage.asking : t.workspacePage.askEos}
        </button>
      </form>

      {askResponse && (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-sm text-gray-700 whitespace-pre-wrap max-h-40 overflow-y-auto">
          {askResponse}
        </div>
      )}

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {summary?.kpi_projects.slice(0, 2).map((k) => (
          <div key={k.label} className="bg-white rounded-xl border border-gray-200 p-5">
            <span className="text-2xl">{k.icon}</span>
            <p className={`text-2xl font-bold mt-2 ${k.color}`}>{k.value}</p>
            <p className="text-sm text-gray-600 mt-1">{k.label}</p>
            {k.trend && <p className="text-xs text-gray-400 mt-0.5">{k.trend}</p>}
          </div>
        ))}
        {summary?.kpi_financial.slice(0, 2).map((k) => (
          <div key={k.label} className="bg-white rounded-xl border border-gray-200 p-5">
            <span className="text-2xl">{k.icon}</span>
            <p className={`text-2xl font-bold mt-2 ${k.color}`}>{k.value}</p>
            <p className="text-sm text-gray-600 mt-1">{k.label}</p>
            {k.trend && <p className="text-xs text-gray-400 mt-0.5">{k.trend}</p>}
          </div>
        ))}
        {(!summary?.kpi_projects.length || !summary?.kpi_financial.length) && (
          <>
            <div className="bg-white rounded-xl border border-gray-200 p-5 text-center text-gray-400">
              <span className="text-3xl">🏗</span>
              <p className="text-lg font-medium mt-2 text-gray-600">{summary?.active_projects ?? 0} {t.workspacePage.activeProjects}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5 text-center text-gray-400">
              <span className="text-3xl">⏳</span>
              <p className="text-lg font-medium mt-2 text-gray-600">{summary?.pending_approvals ?? 0} {t.workspacePage.pendingApprovals}</p>
            </div>
          </>
        )}
      </div>

      {/* Pending approvals + Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pending approvals */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <span>⏳</span> {t.workspacePage.pendingApprovals} ({tasks.filter((t) => t.type === "approval" && t.status !== "done").length})
          </h3>
          {tasks.filter((t) => t.type === "approval" && t.status !== "done").length === 0 ? (
            <p className="text-gray-400 text-sm py-4">{t.workspacePage.noPendingApprovals}</p>
          ) : (
            <div className="space-y-3">
              {tasks
                .filter((task) => task.type === "approval" && task.status !== "done")
                .slice(0, 5)
                .map((task) => (
                  <div
                    key={task.id}
                    className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
                  >
                    <span
                      className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                        task.priority === "high"
                          ? "bg-red-100 text-red-700"
                          : task.priority === "medium"
                          ? "bg-amber-100 text-amber-700"
                          : "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {task.priority}
                    </span>
                    <span className="flex-1 text-sm text-gray-800 truncate">{task.title}</span>
                    <button className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                      {t.workspacePage.approveBtn}
                    </button>
                  </div>
                ))}
            </div>
          )}
        </div>

        {/* Alerts */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <span>🔔</span> {t.workspacePage.latestAlerts}
          </h3>
          {alerts.length === 0 ? (
            <p className="text-gray-400 text-sm py-4">{t.workspacePage.noNewAlerts}</p>
          ) : (
            <div className="space-y-3">
              {alerts.slice(0, 5).map((a) => (
                <div
                  key={a.id}
                  className={`flex items-start gap-3 p-3 rounded-lg ${
                    a.type === "error"
                      ? "bg-red-50 border border-red-100"
                      : a.type === "warning"
                      ? "bg-amber-50 border border-amber-100"
                      : "bg-blue-50 border border-blue-100"
                  }`}
                >
                  <span className="mt-0.5">
                    {a.type === "error" ? "🔴" : a.type === "warning" ? "🟡" : "🔵"}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-gray-800">{a.title}</p>
                    <p className="text-xs text-gray-600 mt-0.5">{a.message}</p>
                    <p className="text-xs text-gray-400 mt-1">{a.time}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* My Tasks */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <span>📋</span> {t.workspacePage.myTasks} ({tasks.filter((t) => t.status !== "done").length})
        </h3>
        {tasks.filter((t) => t.status !== "done").length === 0 ? (
          <p className="text-gray-400 text-sm py-4">{t.workspacePage.noActiveTasks}</p>
        ) : (
          <div className="space-y-2">
            {tasks
              .filter((task) => task.status !== "done")
              .slice(0, 8)
              .map((task) => (
                <div
                  key={task.id}
                  className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg cursor-pointer"
                >
                  <input
                    type="checkbox"
                    className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    defaultChecked={task.status === "done"}
                  />
                  <span className="flex-1 text-sm text-gray-700">{task.title}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      task.type === "approval"
                        ? "bg-purple-100 text-purple-700"
                        : task.type === "action"
                        ? "bg-blue-100 text-blue-700"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {task.type}
                  </span>
                  {task.due && (
                    <span className="text-xs text-gray-400">{task.due}</span>
                  )}
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}
