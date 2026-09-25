import { useState, useEffect, useCallback } from 'react';
import { useI18n } from '../i18n';

// ---------------------------------------------------------------------------
// API response types
// ---------------------------------------------------------------------------

interface RuleCondition {
  field: string;
  op: string;
  value: string | number | boolean | null;
}

interface NotifyAction {
  type: 'notify';
  title: string;
  message: string;
  user_id?: string;
  role?: string;
}

interface PublishEventAction {
  type: 'publish_event';
  event_type: string;
  payload?: Record<string, unknown>;
  entity_type?: string;
  entity_id?: string;
}

interface AuditAction {
  type: 'audit';
  message?: string;
}

type RuleAction = NotifyAction | PublishEventAction | AuditAction;

interface RuleResponse {
  id: string;
  name: string;
  description: string | null;
  event_type: string;
  conditions: RuleCondition[];
  actions: RuleAction[];
  priority: number;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

interface ExecutionResponse {
  id: string;
  rule_id: string;
  rule_name: string;
  matched: boolean;
  detail: string | null;
  executed_at: string;
}

interface RulesListResponse {
  items: RuleResponse[];
  total: number;
  limit: number;
  offset: number;
}

interface ExecutionsListResponse {
  items: ExecutionResponse[];
  total: number;
}

// ---------------------------------------------------------------------------
// Form types
// ---------------------------------------------------------------------------

interface ConditionForm {
  field: string;
  op: string;
  value: string;
}

interface NotifyActionForm {
  type: 'notify';
  title: string;
  message: string;
  role: string;
}

interface PublishEventActionForm {
  type: 'publish_event';
  event_type: string;
  entity_type: string;
}

interface AuditActionForm {
  type: 'audit';
  message: string;
}

type ActionForm = NotifyActionForm | PublishEventActionForm | AuditActionForm;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const EVENT_TYPE_PRESETS = [
  'workflow.instance.started',
  'workflow.transition.applied',
  'workflow.transition.rejected',
  'workflow.instance.completed',
  'graph.relationship.created',
  'construction.project.created',
  'report.run.completed',
  'auth.user.registered',
];

const OP_OPTIONS = [
  'exists',
  'eq',
  'neq',
  'gt',
  'gte',
  'lt',
  'lte',
  'contains',
  'not_contains',
  'in',
  'starts_with',
];

const ACTION_TYPES = ['notify', 'publish_event', 'audit'] as const;

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------

const inputCls =
  'w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white';

const labelCls = 'block text-xs font-medium text-gray-500 mb-1';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function conditionValue(value: string, op: string): string | number | null {
  if (op === 'exists' || value === '') return null;
  const num = Number(value);
  if (value.trim() !== '' && Number.isFinite(num)) return num;
  return value;
}

function toConditionPayload(c: ConditionForm): RuleCondition {
  return { field: c.field, op: c.op, value: conditionValue(c.value, c.op) };
}

function toActionPayload(a: ActionForm): RuleAction {
  switch (a.type) {
    case 'notify': {
      const payload: NotifyAction = { type: 'notify', title: a.title, message: a.message };
      if (a.role !== '') payload.role = a.role;
      return payload;
    }
    case 'publish_event': {
      const payload: PublishEventAction = {
        type: 'publish_event',
        event_type: a.event_type,
      };
      if (a.entity_type !== '') payload.entity_type = a.entity_type;
      return payload;
    }
    case 'audit': {
      const payload: AuditAction = { type: 'audit' };
      if (a.message !== '') payload.message = a.message;
      return payload;
    }
  }
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString();
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

// ---------------------------------------------------------------------------
// RuleCard
// ---------------------------------------------------------------------------

function RuleCard({ rule }: { rule: RuleResponse }) {
  const { t } = useI18n();
  const firstAction = rule.actions[0];
  let actionSummary = t.rulesPage.noActions;
  if (firstAction) {
    if (firstAction.type === 'notify') {
      actionSummary = `notify: ${firstAction.title || 'Untitled'}`;
    } else if (firstAction.type === 'publish_event') {
      actionSummary = `publish: ${firstAction.event_type}`;
    } else if (firstAction.type === 'audit') {
      actionSummary = `audit: ${firstAction.message || 'log'}`;
    }
  }

  const condCount = rule.conditions.length;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col gap-3 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className={`w-2.5 h-2.5 rounded-full shrink-0 ${
              rule.enabled ? 'bg-green-500' : 'bg-gray-300'
            }`}
            title={rule.enabled ? 'Enabled' : 'Disabled'}
          />
          <h4 className="font-medium text-gray-900 truncate">{rule.name}</h4>
        </div>
        <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600 shrink-0">
          P{rule.priority}
        </span>
      </div>

      <span className="inline-flex self-start items-center px-2 py-0.5 rounded-md text-xs font-medium bg-blue-50 text-blue-700 font-mono">
        {rule.event_type}
      </span>

      <div className="flex flex-wrap gap-2 text-xs text-gray-500">
        <span>
          {condCount} condition{condCount !== 1 ? 's' : ''}
        </span>
        <span aria-hidden="true">&middot;</span>
        <span>{actionSummary}</span>
      </div>

      <div className="pt-2 border-t border-gray-100 text-xs text-gray-400">
        Created {formatDate(rule.created_at)}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ExecutionsTable
// ---------------------------------------------------------------------------

function ExecutionsTable({ executions }: { executions: ExecutionResponse[] }) {
  const { t } = useI18n();
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <h3 className="font-medium text-gray-900">{t.rulesPage.ruleExecutions}</h3>
        <p className="text-sm text-gray-500 mt-0.5">{t.rulesPage.recentExecutionHistory}</p>
      </div>
      {executions.length === 0 ? (
        <p className="px-5 py-8 text-sm text-gray-500">{t.rulesPage.noExecutions}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <th className="px-5 py-3">{t.rulesPage.colRule}</th>
                <th className="px-5 py-3">{t.rulesPage.colMatched}</th>
                <th className="px-5 py-3">{t.rulesPage.colDetail}</th>
                <th className="px-5 py-3">{t.rulesPage.colExecutedAt}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {executions.map((exec) => (
                <tr key={exec.id}>
                  <td className="px-5 py-3 font-medium text-gray-900">{exec.rule_name}</td>
                  <td className="px-5 py-3">
                    <span
                      className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                        exec.matched ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {exec.matched ? t.rulesPage.matched : t.rulesPage.noMatch}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-gray-500 max-w-xs truncate">
                    {exec.detail || '\u2014'}
                  </td>
                  <td className="px-5 py-3 text-gray-400 text-xs whitespace-nowrap">
                    {formatDateTime(exec.executed_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ActionFormRow
// ---------------------------------------------------------------------------

function ActionFormRow({
  action,
  onUpdate,
  onRemove,
  canRemove,
}: {
  action: ActionForm;
  onUpdate: (action: ActionForm) => void;
  onRemove: () => void;
  canRemove: boolean;
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-3 space-y-3">
      <div className="flex items-center justify-between">
        <select
          value={action.type}
          onChange={(e) => {
            const v = e.target.value;
            if (v === 'notify') {
              onUpdate({ type: 'notify', title: '', message: '', role: '' });
            } else if (v === 'publish_event') {
              onUpdate({
                type: 'publish_event',
                event_type: 'event.alerted',
                entity_type: '',
              });
            } else if (v === 'audit') {
              onUpdate({ type: 'audit', message: '' });
            }
          }}
          className="w-44 px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white"
        >
          {ACTION_TYPES.map((at) => (
            <option key={at} value={at}>
              {at}
            </option>
          ))}
        </select>
        {canRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="text-xs text-red-500 hover:text-red-700"
          >
            Remove
          </button>
        )}
      </div>

      {action.type === 'notify' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className={labelCls}>Title</label>
            <input
              value={action.title}
              onChange={(e) => onUpdate({ ...action, title: e.target.value })}
              className={inputCls}
              placeholder="Alert title"
            />
          </div>
          <div>
            <label className={labelCls}>Message</label>
            <input
              value={action.message}
              onChange={(e) => onUpdate({ ...action, message: e.target.value })}
              className={inputCls}
              placeholder="Notification message"
            />
          </div>
          <div>
            <label className={labelCls}>Role (optional)</label>
            <input
              value={action.role}
              onChange={(e) => onUpdate({ ...action, role: e.target.value })}
              className={inputCls}
              placeholder="e.g. manager"
            />
          </div>
        </div>
      )}

      {action.type === 'publish_event' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className={labelCls}>Event Type</label>
            <input
              value={action.event_type}
              onChange={(e) => onUpdate({ ...action, event_type: e.target.value })}
              className={inputCls}
              placeholder="event.alerted"
              required
            />
          </div>
          <div>
            <label className={labelCls}>Entity Type (optional)</label>
            <input
              value={action.entity_type}
              onChange={(e) => onUpdate({ ...action, entity_type: e.target.value })}
              className={inputCls}
              placeholder="e.g. purchase_request"
            />
          </div>
        </div>
      )}

      {action.type === 'audit' && (
        <div>
          <label className={labelCls}>Message (optional)</label>
          <input
            value={action.message}
            onChange={(e) => onUpdate({ ...action, message: e.target.value })}
            className={inputCls}
            placeholder="Audit log message"
          />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// RulesPage
// ---------------------------------------------------------------------------

export function RulesPage({ token, role }: { token: string; role: string }) {
  const { t } = useI18n();
  const [rules, setRules] = useState<RuleResponse[]>([]);
  const [executions, setExecutions] = useState<ExecutionResponse[]>([]);
  const [showExecutions, setShowExecutions] = useState(true);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const [formName, setFormName] = useState('');
  const [formEventType, setFormEventType] = useState('');
  const [formConditions, setFormConditions] = useState<ConditionForm[]>([
    { field: '', op: 'eq', value: '' },
  ]);
  const [formActions, setFormActions] = useState<ActionForm[]>([
    { type: 'notify', title: '', message: '', role: '' },
  ]);
  const [formPriority, setFormPriority] = useState(100);
  const [formEnabled, setFormEnabled] = useState(true);

  const fetchRules = useCallback(async () => {
    const res = await fetch('/api/v1/rules', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      const data = (await res.json()) as RulesListResponse;
      setRules(data.items ?? []);
    }
  }, [token]);

  const fetchExecutions = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/rules/executions', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = (await res.json()) as ExecutionsListResponse;
        setExecutions(data.items ?? []);
      } else {
        setShowExecutions(false);
      }
    } catch {
      setShowExecutions(false);
    }
  }, [token]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([fetchRules(), fetchExecutions()])
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [fetchRules, fetchExecutions]);

  // ---- condition helpers ----

  const addCondition = () => {
    setFormConditions((prev) =>
      prev.length < 3 ? [...prev, { field: '', op: 'eq', value: '' }] : prev
    );
  };

  const removeCondition = (index: number) => {
    setFormConditions((prev) => prev.filter((_, i) => i !== index));
  };

  const updateCondition = (index: number, patch: Partial<ConditionForm>) => {
    setFormConditions((prev) => prev.map((c, i) => (i === index ? { ...c, ...patch } : c)));
  };

  // ---- action helpers ----

  const addAction = (type: ActionForm['type']) => {
    setFormActions((prev) => {
      if (type === 'notify') {
        return [...prev, { type: 'notify', title: '', message: '', role: '' }];
      }
      if (type === 'publish_event') {
        const defaultEt = formEventType ? `${formEventType}.alerted` : 'event.alerted';
        return [...prev, { type: 'publish_event', event_type: defaultEt, entity_type: '' }];
      }
      return [...prev, { type: 'audit', message: '' }];
    });
  };

  const removeAction = (index: number) => {
    setFormActions((prev) => prev.filter((_, i) => i !== index));
  };

  const updateAction = (index: number, replacement: ActionForm) => {
    setFormActions((prev) => prev.map((a, i) => (i === index ? replacement : a)));
  };

  // ---- form reset / submit ----

  const resetForm = () => {
    setFormName('');
    setFormEventType('');
    setFormConditions([{ field: '', op: 'eq', value: '' }]);
    setFormActions([{ type: 'notify', title: '', message: '', role: '' }]);
    setFormPriority(100);
    setFormEnabled(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const body = {
        name: formName,
        event_type: formEventType,
        conditions: formConditions.map(toConditionPayload),
        actions: formActions.map(toActionPayload),
        priority: formPriority,
        enabled: formEnabled,
      };
      const res = await fetch('/api/v1/rules', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }
      setShowForm(false);
      resetForm();
      await fetchRules();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create rule');
    } finally {
      setSubmitting(false);
    }
  };

  // ---- render ----

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{t.rulesPage.title}</h2>
          <p className="text-gray-500 mt-1">{t.rulesPage.subtitle}</p>
        </div>
        {role === 'admin' && (
          <button
            onClick={() => {
              setShowForm((v) => !v);
              setError('');
            }}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors shrink-0"
          >
            {showForm ? t.rulesPage.cancel : t.rulesPage.newRule}
          </button>
        )}
      </div>

      {/* Create form */}
      {role !== 'viewer' && showForm && (
        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-xl border border-gray-200 p-5 space-y-5"
        >
          <h3 className="font-medium text-gray-900">{t.rulesPage.createRule}</h3>

          {/* Basic fields */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className={labelCls}>{t.rulesPage.name}</label>
              <input
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                className={inputCls}
                placeholder={t.rulesPage.namePlaceholder}
                required
              />
            </div>
            <div>
              <label className={labelCls}>{t.rulesPage.eventType}</label>
              <input
                list="rule-evt-presets"
                value={formEventType}
                onChange={(e) => setFormEventType(e.target.value)}
                className={inputCls}
                placeholder="purchase_request.created"
                required
              />
              <datalist id="rule-evt-presets">
                {EVENT_TYPE_PRESETS.map((p) => (
                  <option key={p} value={p} />
                ))}
              </datalist>
            </div>
            <div className="flex gap-4">
              <div className="flex-1">
                <label className={labelCls}>{t.rulesPage.priority}</label>
                <input
                  type="number"
                  value={formPriority}
                  onChange={(e) => setFormPriority(Number(e.target.value) || 100)}
                  className={inputCls}
                  min={0}
                  max={1000}
                />
              </div>
              <div className="flex items-end pb-2">
                <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={formEnabled}
                    onChange={(e) => setFormEnabled(e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  {t.rulesPage.enabled}
                </label>
              </div>
            </div>
          </div>

          {/* Conditions */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">{t.rulesPage.conditions}</span>
              {formConditions.length < 3 && (
                <button
                  type="button"
                  onClick={addCondition}
                  className="text-xs text-blue-600 hover:text-blue-800"
                >
                  + {t.rulesPage.addCondition}
                </button>
              )}
            </div>
            <div className="space-y-2">
              {formConditions.map((cond, i) => (
                <div key={i} className="flex items-center gap-2">
                  <input
                    value={cond.field}
                    onChange={(e) => updateCondition(i, { field: e.target.value })}
                    className={`${inputCls} flex-1`}
                    placeholder={t.rulesPage.fieldPlaceholder}
                  />
                  <select
                    value={cond.op}
                    onChange={(e) => updateCondition(i, { op: e.target.value })}
                    className={`${inputCls} w-36`}
                  >
                    {OP_OPTIONS.map((op) => (
                      <option key={op} value={op}>
                        {op}
                      </option>
                    ))}
                  </select>
                  {cond.op !== 'exists' ? (
                    <input
                      value={cond.value}
                      onChange={(e) => updateCondition(i, { value: e.target.value })}
                      className={`${inputCls} w-36`}
                      placeholder={t.rulesPage.valuePlaceholder}
                    />
                  ) : (
                    <div
                      className={`${inputCls} w-36 bg-gray-50 text-gray-400 text-sm flex items-center`}
                    >
                      null
                    </div>
                  )}
                  {formConditions.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeCondition(i)}
                      className="text-xs text-red-500 hover:text-red-700 shrink-0"
                    >
                      &#x2715;
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">{t.rulesPage.actions}</span>
              <div className="flex gap-2">
                {ACTION_TYPES.map((at) => (
                  <button
                    key={at}
                    type="button"
                    onClick={() => addAction(at)}
                    className="text-xs text-blue-600 hover:text-blue-800"
                  >
                    + {at}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-3">
              {formActions.map((action, i) => (
                <ActionFormRow
                  key={i}
                  action={action}
                  onUpdate={(replacement) => updateAction(i, replacement)}
                  onRemove={() => removeAction(i)}
                  canRemove={formActions.length > 1}
                />
              ))}
            </div>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {submitting ? `${t.rulesPage.creating}\u2026` : t.rulesPage.createRuleButton}
            </button>
          </div>
        </form>
      )}

      {/* Rules grid */}
      {rules.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <div className="w-16 h-16 mx-auto bg-gray-100 rounded-full flex items-center justify-center mb-4">
            <svg
              className="w-8 h-8 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M3 10h11M9 3v4M12 21H6a3 3 0 01-3-3V6a3 3 0 013-3h5l6 6v9a3 3 0 01-3 3h-2M19 16v6M16 19h6"
              />
            </svg>
          </div>
          <h3 className="text-gray-900 font-medium">{t.rulesPage.noRulesYet}</h3>
          <p className="text-gray-500 text-sm mt-1">
            {t.rulesPage.noRulesHint}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {rules.map((rule) => (
            <RuleCard key={rule.id} rule={rule} />
          ))}
        </div>
      )}

      {/* Executions */}
      {showExecutions && <ExecutionsTable executions={executions} />}
    </div>
  );
}
