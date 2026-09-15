import { useEffect, useState } from 'react';
import { api } from '../api';

type WorkspaceFeed = {
  entity_counts: Array<{ entity_code: string; count: number }>;
  approvals_pending: Array<{
    task_id: string;
    workflow_code: string;
    action: string;
    to_state: string;
  }>;
  workflows_needing_action: Array<{
    instance_id: string;
    workflow_code: string;
    current_state: string;
  }>;
  recent_events: Array<{ event_type: string; entity_type?: string; occurred_at: string }>;
  recent_rule_firings: Array<{ rule_name: string; executed_at: string }>;
  report_count: number;
};

export function WorkspacePage({
  token,
  onOpenObjects,
}: {
  token: string;
  onOpenObjects: () => void;
}) {
  const [feed, setFeed] = useState<WorkspaceFeed | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api<WorkspaceFeed>('/analytics/home', token)
      .then(setFeed)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Unable to load workspace')
      );
  }, [token]);

  return (
    <main className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">2TO / EOS</p>
          <h1>Operating workspace</h1>
          <p className="muted">
            Attention, approvals, business activity, and source-backed operating context.
          </p>
        </div>
        <button onClick={onOpenObjects}>Open business objects</button>
      </header>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {!feed && !error && <p className="muted">Loading your workspace…</p>}
      {feed && (
        <div className="grid">
          <section className="card">
            <h2>My approvals</h2>
            <p className="metric">{feed.approvals_pending.length}</p>
            <p className="muted">Pending decisions assigned to your role.</p>
          </section>
          <section className="card">
            <h2>Work needing action</h2>
            <p className="metric">{feed.workflows_needing_action.length}</p>
            <p className="muted">Active workflow instances in your scope.</p>
          </section>
          <section className="card">
            <h2>Saved reports</h2>
            <p className="metric">{feed.report_count}</p>
            <p className="muted">Reusable KPI definitions available to this tenant.</p>
          </section>
          <section className="card">
            <h2>Business objects</h2>
            <ul>
              {feed.entity_counts.map((item) => (
                <li key={item.entity_code}>
                  {item.entity_code}: {item.count}
                </li>
              ))}
            </ul>
          </section>
          <section className="card">
            <h2>Recent changes</h2>
            <ul>
              {feed.recent_events.map((item, index) => (
                <li key={`${item.event_type}-${index}`}>
                  {item.event_type} · {item.entity_type ?? 'system'}
                </li>
              ))}
            </ul>
          </section>
          <section className="card">
            <h2>Rule activity</h2>
            <ul>
              {feed.recent_rule_firings.map((item, index) => (
                <li key={`${item.rule_name}-${index}`}>{item.rule_name}</li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </main>
  );
}
