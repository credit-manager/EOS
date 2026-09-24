import { useState, useEffect, useCallback } from 'react';
import { useI18n } from '../i18n';

interface WorkflowInstance {
  id: string;
  tenant_id: string;
  workflow_code: string;
  workflow_version: number;
  reference_type: string;
  reference_id: string;
  current_state: string;
  status: string;
}

interface Approval {
  id: string;
  workflow_instance_id: string;
  action: string;
  from_state: string;
  to_state: string;
  status: string;
  requested_by: string;
  decided_by: string | null;
}

interface WorkflowTemplate {
  code: string;
  name: string;
  states: Array<{ code: string; name: string; is_start: boolean; is_end: boolean }>;
  transitions: Array<{
    code: string;
    from: string;
    to: string;
    require_approval: boolean;
    actor_roles: string[];
  }>;
}

interface HistoryEntry {
  id: string;
  from_state: string;
  to_state: string;
  action: string;
  actor: string;
  timestamp: string;
  metadata: Record<string, unknown>;
}

interface AvailableTransition {
  code: string;
  from_state: string;
  to_state: string;
  require_approval: boolean;
}

type Tab = 'instances' | 'approvals' | 'templates' | 'history';

const STATUS_STYLES: Record<string, string> = {
  running: 'bg-green-100 text-green-700',
  completed: 'bg-blue-100 text-blue-700',
  failed: 'bg-red-100 text-red-700',
  blocked: 'bg-red-100 text-red-700',
  pending: 'bg-amber-100 text-amber-700',
};

const STATE_COLORS: Record<string, string> = {
  draft: 'bg-gray-200 text-gray-700 border-gray-400',
  pending_manager: 'bg-amber-100 text-amber-700 border-amber-400',
  pending_finance: 'bg-blue-100 text-blue-700 border-blue-400',
  approved: 'bg-green-100 text-green-700 border-green-400',
  rejected: 'bg-red-100 text-red-700 border-red-400',
  cancelled: 'bg-gray-100 text-gray-500 border-gray-300',
};

function StatusBadge({ status }: { status: string }) {
  const base = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium';
  const styles = STATUS_STYLES[status] ?? 'bg-gray-100 text-gray-700';
  return <span className={`${base} ${styles}`}>{status}</span>;
}

function TabButton({
  label,
  count,
  active,
  onClick,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
        active ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
      }`}
    >
      {label}
      <span
        className={`ml-2 px-1.5 py-0.5 rounded-full text-xs ${
          active ? 'bg-blue-100 text-blue-700' : 'bg-gray-200 text-gray-500'
        }`}
      >
        {count}
      </span>
    </button>
  );
}

export function WorkflowsPage({ token, role }: { token: string; role: string }) {
  const { t } = useI18n();
  const [instances, setInstances] = useState<WorkflowInstance[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [selectedInstanceId, setSelectedInstanceId] = useState<string | null>(null);
  const [historyEntries, setHistoryEntries] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>('instances');

  const fetchData = useCallback(() => {
    setLoading(true);
    Promise.all([
      fetch('/api/v1/workflow/instances', {
        headers: { Authorization: `Bearer ${token}` },
      }).then((r) => (r.ok ? r.json() : { instances: [] })),
      fetch('/api/v1/workflow/pending', {
        headers: { Authorization: `Bearer ${token}` },
      }).then((r) => (r.ok ? r.json() : { approvals: [] })),
      fetch('/api/v1/workflow/templates', {
        headers: { Authorization: `Bearer ${token}` },
      }).then((r) => (r.ok ? r.json() : { templates: [] })),
    ])
      .then(([instData, approvalData, templateData]) => {
        setInstances(instData.instances || []);
        setApprovals(approvalData.approvals || []);
        setTemplates(templateData.templates || []);
      })
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const loadHistory = async (instanceId: string) => {
    setSelectedInstanceId(instanceId);
    setActiveTab('history');
    try {
      const res = await fetch(`/api/v1/workflow/history/${instanceId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = res.ok ? await res.json() : { history: [] };
      setHistoryEntries(data.history || []);
    } catch {
      setHistoryEntries([]);
    }
  };

  const handleTransition = async (instanceId: string, toState: string) => {
    await fetch('/api/v1/workflow/transition', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ instance_id: instanceId, to_state: toState }),
    });
    fetchData();
  };

  const handleApproveDecision = async (approvalId: string, decision: 'approve' | 'reject') => {
    await fetch('/api/v1/workflow/approve', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ approval_id: approvalId, decision }),
    });
    fetchData();
  };

  const handleDelegate = async (instanceId: string) => {
    await fetch('/api/v1/workflow/transition', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ instance_id: instanceId, to_state: 'delegated' }),
    });
    fetchData();
  };

  const handleCancel = async (instanceId: string) => {
    await fetch('/api/v1/workflow/transition', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ instance_id: instanceId, to_state: 'cancelled' }),
    });
    if (selectedInstanceId === instanceId) {
      setSelectedInstanceId(null);
      setHistoryEntries([]);
    }
    fetchData();
  };

  const handleStartWorkflow = async (templateCode: string, referenceType: string, referenceId: string) => {
    await fetch('/api/v1/workflow/instances', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        workflow_code: templateCode,
        reference_type: referenceType,
        reference_id: referenceId,
      }),
    });
    fetchData();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  const selectedInstance = instances.find((inst) => inst.id === selectedInstanceId) || null;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">{t.workflowsPage.title}</h2>
        <p className="text-gray-500 mt-1">{t.workflowsPage.subtitle}</p>
      </div>

      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        <TabButton
          label={t.workflowsPage.tabInstances}
          count={instances.length}
          active={activeTab === 'instances'}
          onClick={() => setActiveTab('instances')}
        />
        <TabButton
          label={t.workflowsPage.tabApprovals}
          count={approvals.length}
          active={activeTab === 'approvals'}
          onClick={() => setActiveTab('approvals')}
        />
        <TabButton
          label={t.workflowsPage.tabTemplates}
          count={templates.length}
          active={activeTab === 'templates'}
          onClick={() => setActiveTab('templates')}
        />
        <TabButton
          label={t.workflowsPage.tabHistory}
          count={historyEntries.length}
          active={activeTab === 'history'}
          onClick={() => setActiveTab('history')}
        />
      </div>

      {activeTab === 'instances' && (
        <InstancesTab
          instances={instances}
          onRefresh={fetchData}
          onSelectInstance={loadHistory}
          onCancel={handleCancel}
          onTransition={handleTransition}
          onStartWorkflow={handleStartWorkflow}
          templates={templates}
          token={token}
        />
      )}

      {activeTab === 'approvals' && (
        <ApprovalsTab
          approvals={approvals}
          role={role}
          onDecision={handleApproveDecision}
          onDelegate={handleDelegate}
          onRefresh={fetchData}
        />
      )}

      {activeTab === 'templates' && <TemplatesTab templates={templates} />}

      {activeTab === 'history' && (
        <HistoryTab
          instance={selectedInstance}
          historyEntries={historyEntries}
          onBack={() => setActiveTab('instances')}
          onCancel={handleCancel}
        />
      )}
    </div>
  );
}

function InstancesTab({
  instances,
  onRefresh,
  onSelectInstance,
  onCancel,
  onTransition,
  onStartWorkflow,
  templates,
  token,
}: {
  instances: WorkflowInstance[];
  onRefresh: () => void;
  onSelectInstance: (id: string) => void;
  onCancel: (id: string) => void;
  onTransition: (id: string, code: string) => void;
  onStartWorkflow: (code: string, refType: string, refId: string) => void;
  templates: WorkflowTemplate[];
  token: string;
}) {
  const { t } = useI18n();
  const [showStartModal, setShowStartModal] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [refType, setRefType] = useState('');
  const [refId, setRefId] = useState('');
  const [expandedInstance, setExpandedInstance] = useState<string | null>(null);
  const [transitionsMap, setTransitionsMap] = useState<Record<string, AvailableTransition[]>>({});

  const loadTransitions = async (instanceId: string) => {
    if (transitionsMap[instanceId]) {
      setExpandedInstance(expandedInstance === instanceId ? null : instanceId);
      return;
    }
    const res = await fetch(`/api/v1/workflow/transitions/${instanceId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = res.ok ? await res.json() : { transitions: [] };
    setTransitionsMap((prev) => ({ ...prev, [instanceId]: data.transitions || [] }));
    setExpandedInstance(instanceId);
  };

  const handleStart = () => {
    if (!selectedTemplate || !refType || !refId) return;
    onStartWorkflow(selectedTemplate, refType, refId);
    setShowStartModal(false);
    setSelectedTemplate('');
    setRefType('');
    setRefId('');
  };

  return (
    <div className="space-y-3">
      <div className="flex justify-end gap-2">
        <button
          onClick={() => setShowStartModal(true)}
          className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
        >
          {t.workflowsPage.startWorkflow}
        </button>
        <button
          onClick={onRefresh}
          className="px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
        >
          {t.workflowsPage.refresh}
        </button>
      </div>

      {instances.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <div className="w-16 h-16 mx-auto bg-gray-100 rounded-full flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <h3 className="text-gray-900 font-medium">{t.workflowsPage.noInstances}</h3>
          <p className="text-gray-500 text-sm mt-1">{t.workflowsPage.noInstancesHint}</p>
        </div>
      ) : (
        instances.map((instance) => (
          <InstanceCard
            key={instance.id}
            instance={instance}
            expanded={expandedInstance === instance.id}
            transitions={transitionsMap[instance.id]}
            onToggle={() => loadTransitions(instance.id)}
            onSelect={() => onSelectInstance(instance.id)}
            onCancel={() => onCancel(instance.id)}
            onTransition={(code) => onTransition(instance.id, code)}
          />
        ))
      )}

      {showStartModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">{t.workflowsPage.startNewWorkflow}</h3>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t.workflowsPage.template}</label>
              <select
                value={selectedTemplate}
                onChange={(e) => setSelectedTemplate(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="">{t.workflowsPage.selectTemplate}</option>
                {templates.map((tpl) => (
                  <option key={tpl.code} value={tpl.code}>
                    {tpl.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t.workflowsPage.referenceType}</label>
              <input
                value={refType}
                onChange={(e) => setRefType(e.target.value)}
                placeholder={t.workflowsPage.referenceTypePlaceholder}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t.workflowsPage.referenceId}</label>
              <input
                value={refId}
                onChange={(e) => setRefId(e.target.value)}
                placeholder={t.workflowsPage.referenceIdPlaceholder}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowStartModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                {t.workflowsPage.cancel}
              </button>
              <button
                onClick={handleStart}
                disabled={!selectedTemplate || !refType || !refId}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {t.workflowsPage.start}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function InstanceCard({
  instance,
  expanded,
  transitions,
  onToggle,
  onSelect,
  onCancel,
  onTransition,
}: {
  instance: WorkflowInstance;
  expanded: boolean;
  transitions: AvailableTransition[] | undefined;
  onToggle: () => void;
  onSelect: () => void;
  onCancel: () => void;
  onTransition: (code: string) => void;
}) {
  const { t } = useI18n();
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div className="space-y-1 cursor-pointer" onClick={onToggle}>
          <div className="flex items-center gap-3">
            <code className="text-sm font-mono text-gray-800 bg-gray-100 px-2 py-0.5 rounded">
              {instance.workflow_code}
            </code>
            <span className="text-xs text-gray-400">v{instance.workflow_version}</span>
            <StatusBadge status={instance.status} />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onSelect}
            className="px-2 py-1 text-xs font-medium text-blue-600 bg-blue-50 rounded hover:bg-blue-100 transition-colors"
          >
            {t.workflowsPage.history}
          </button>
          {instance.status === 'running' && (
            <button
              onClick={onCancel}
              className="px-2 py-1 text-xs font-medium text-red-600 bg-red-50 rounded hover:bg-red-100 transition-colors"
            >
              {t.workflowsPage.cancelWorkflow}
            </button>
          )}
          <button onClick={onToggle} className="text-gray-400 hover:text-gray-600">
            <svg className={`w-4 h-4 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500">{t.workflowsPage.currentState}</span>
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-700">
          {instance.current_state}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-gray-500">{t.workflowsPage.instanceId}</span>
          <p className="font-mono text-gray-700 mt-0.5">{instance.id.slice(0, 8)}</p>
        </div>
        <div>
          <span className="text-gray-500">{t.workflowsPage.tenant}</span>
          <p className="font-mono text-gray-700 mt-0.5">{instance.tenant_id.slice(0, 8)}</p>
        </div>
        <div>
          <span className="text-gray-500">{t.workflowsPage.referenceTypeLabel}</span>
          <p className="text-gray-700 mt-0.5">{instance.reference_type}</p>
        </div>
        <div>
          <span className="text-gray-500">{t.workflowsPage.referenceIdLabel}</span>
          <p className="font-mono text-gray-700 mt-0.5">{instance.reference_id.slice(0, 8)}</p>
        </div>
      </div>

      {expanded && transitions && (
        <div className="border-t border-gray-100 pt-3 space-y-2">
          <p className="text-xs font-medium text-gray-500 uppercase">{t.workflowsPage.availableTransitions}</p>
          {transitions.length === 0 ? (
            <p className="text-sm text-gray-400">{t.workflowsPage.noTransitions}</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {transitions.map((tr) => (
                <button
                  key={tr.code}
                  onClick={() => onTransition(tr.to_state)}
                  className="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  title={`${tr.from_state} → ${tr.to_state}`}
                >
                  {tr.code}
                  {tr.require_approval && <span className="ml-1 opacity-60">({t.workflowsPage.approval})</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ApprovalsTab({
  approvals,
  role,
  onDecision,
  onDelegate,
  onRefresh,
}: {
  approvals: Approval[];
  role: string;
  onDecision: (approvalId: string, decision: 'approve' | 'reject') => void;
  onDelegate: (instanceId: string) => void;
  onRefresh: () => void;
}) {
  const { t } = useI18n();

  if (approvals.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
        <div className="w-16 h-16 mx-auto bg-green-50 rounded-full flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 className="text-gray-900 font-medium">{t.workflowsPage.allCaughtUp}</h3>
        <p className="text-gray-500 text-sm mt-1">{t.workflowsPage.noPendingApprovals}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button
          onClick={onRefresh}
          className="px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
        >
          {t.workflowsPage.refresh}
        </button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  {t.workflowsPage.colAction}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  {t.workflowsPage.colTransition}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  {t.workflowsPage.colInstance}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  {t.workflowsPage.colStatus}
                </th>
                {role !== 'viewer' && (
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    {t.workflowsPage.colActions}
                  </th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {approvals.map((approval) => (
                <tr key={approval.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-700">{approval.action}</td>
                  <td className="px-4 py-3">
                    <span className="text-gray-700">{approval.from_state}</span>
                    <span className="mx-2 text-gray-400">&rarr;</span>
                    <span className="text-gray-700">{approval.to_state}</span>
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-600">
                    {approval.workflow_instance_id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={approval.status} />
                  </td>
                  {role !== 'viewer' && (
                    <td className="px-4 py-3 text-right space-x-2">
                      {approval.status === 'pending' && (
                        <>
                          <button
                            onClick={() => onDecision(approval.id, 'approve')}
                            className="px-3 py-1 bg-green-600 text-white text-xs font-medium rounded-md hover:bg-green-700 transition-colors"
                          >
                            {t.workflowsPage.approve}
                          </button>
                          <button
                            onClick={() => onDecision(approval.id, 'reject')}
                            className="px-3 py-1 bg-red-600 text-white text-xs font-medium rounded-md hover:bg-red-700 transition-colors"
                          >
                            {t.workflowsPage.reject}
                          </button>
                          <button
                            onClick={() => onDelegate(approval.workflow_instance_id)}
                            className="px-3 py-1 bg-amber-500 text-white text-xs font-medium rounded-md hover:bg-amber-600 transition-colors"
                          >
                            {t.workflowsPage.delegate}
                          </button>
                        </>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function TemplatesTab({ templates }: { templates: WorkflowTemplate[] }) {
  const { t } = useI18n();

  if (templates.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
        <div className="w-16 h-16 mx-auto bg-purple-50 rounded-full flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
          </svg>
        </div>
        <h3 className="text-gray-900 font-medium">{t.workflowsPage.noTemplates}</h3>
        <p className="text-gray-500 text-sm mt-1">{t.workflowsPage.noTemplatesHint}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {templates.map((tpl) => (
        <div key={tpl.code} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <div className="flex items-center gap-3">
            <code className="text-sm font-mono text-purple-700 bg-purple-50 px-2 py-0.5 rounded">
              {tpl.code}
            </code>
            <h3 className="text-lg font-semibold text-gray-900">{tpl.name}</h3>
          </div>

          <div className="space-y-2">
            <p className="text-xs font-medium text-gray-500 uppercase">{t.workflowsPage.states}</p>
            <div className="flex flex-wrap gap-2">
              {tpl.states.map((state) => (
                <div
                  key={state.code}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border ${
                    STATE_COLORS[state.code] ?? 'bg-gray-50 text-gray-600 border-gray-200'
                  }`}
                >
                  {state.name}
                  {state.is_start && <span className="ml-1 opacity-60">(start)</span>}
                  {state.is_end && <span className="ml-1 opacity-60">(end)</span>}
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs font-medium text-gray-500 uppercase">{t.workflowsPage.transitions}</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {tpl.transitions.map((tr) => (
                <div
                  key={tr.code}
                  className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg text-xs"
                >
                  <span className="font-mono text-gray-700">{tr.from}</span>
                  <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                  <span className="font-mono text-gray-700">{tr.to}</span>
                  {tr.require_approval && (
                    <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-[10px] font-medium">
                      {t.workflowsPage.approval}
                    </span>
                  )}
                  <span className="ml-auto text-gray-400">{tr.actor_roles.join(', ')}</span>
                </div>
              ))}
            </div>
          </div>

          <StateDiagram template={tpl} />
        </div>
      ))}
    </div>
  );
}

function StateDiagram({ template }: { template: WorkflowTemplate }) {
  const { t } = useI18n();
  const stateMap = new Map(template.states.map((s) => [s.code, s]));
  const startState = template.states.find((s) => s.is_start);

  const buildRows = () => {
    const rows: string[][] = [];
    const visited = new Set<string>();
    const queue: string[][] = startState ? [[startState.code]] : [[]];

    while (queue.length > 0) {
      const row = queue.shift()!;
      const current = row[row.length - 1];
      if (visited.has(current)) continue;
      visited.add(current);

      const outgoing = template.transitions.filter((tr) => tr.from === current);
      const nextStates = outgoing.map((tr) => tr.to);

      if (nextStates.length === 0) {
        rows.push(row);
      } else {
        for (const next of nextStates) {
          queue.push([...row, next]);
        }
      }
    }
    return rows.length > 0 ? rows : [template.states.map((s) => s.code)];
  };

  const rows = buildRows();

  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-gray-500 uppercase">{t.workflowsPage.stateDiagram}</p>
      <div className="overflow-x-auto p-3 bg-gray-50 rounded-lg">
        {rows.map((row, ri) => (
          <div key={ri} className="flex items-center gap-1 mb-2">
            {row.map((stateCode, si) => {
              const state = stateMap.get(stateCode);
              if (!state) return null;
              return (
                <div key={si} className="flex items-center gap-1">
                  {si > 0 && (
                    <svg className="w-6 h-4 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                  )}
                  <div
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border ${
                      STATE_COLORS[state.code] ?? 'bg-gray-100 text-gray-600 border-gray-300'
                    }`}
                  >
                    {state.name}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
        {template.transitions
          .filter((tr) => {
            const fromRow = rows.findIndex((r) => r.includes(tr.from));
            const toRow = rows.findIndex((r) => r.includes(tr.to));
            return fromRow !== toRow;
          })
          .map((tr, i) => (
            <div key={i} className="text-[10px] text-gray-400 mt-1">
              {tr.from} &rarr; {tr.to}
            </div>
          ))}
      </div>
    </div>
  );
}

function HistoryTab({
  instance,
  historyEntries,
  onBack,
  onCancel,
}: {
  instance: WorkflowInstance | null;
  historyEntries: HistoryEntry[];
  onBack: () => void;
  onCancel: (id: string) => void;
}) {
  const { t } = useI18n();

  if (!instance) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
        <p className="text-gray-500 text-sm">{t.workflowsPage.selectInstanceHint}</p>
        <button
          onClick={onBack}
          className="mt-4 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
        >
          {t.workflowsPage.goToInstances}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="text-gray-400 hover:text-gray-600">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{t.workflowsPage.workflowHistory}</h3>
            <code className="text-xs font-mono text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
              {instance.id.slice(0, 8)}
            </code>
          </div>
        </div>
        {instance.status === 'running' && (
          <button
            onClick={() => onCancel(instance.id)}
            className="px-3 py-1.5 text-sm font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
          >
            {t.workflowsPage.cancelWorkflow}
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">{t.workflowsPage.currentState}</span>
          <StatusBadge status={instance.status} />
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-700">
            {instance.current_state}
          </span>
        </div>
      </div>

      {historyEntries.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <p className="text-gray-500 text-sm">{t.workflowsPage.noHistoryEntries}</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <p className="text-xs font-medium text-gray-500 uppercase mb-4">{t.workflowsPage.timeline}</p>
          <div className="relative">
            <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />
            <div className="space-y-6">
              {historyEntries.map((entry) => {
                const color = STATE_COLORS[entry.to_state] ?? 'bg-gray-200 text-gray-600 border-gray-300';
                const dotColor = color.split(' ')[0];
                return (
                  <div key={entry.id} className="relative flex gap-4">
                    <div className={`w-8 h-8 rounded-full ${dotColor} border-2 flex items-center justify-center z-10 flex-shrink-0`}>
                      <div className="w-2 h-2 rounded-full bg-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-400">{entry.from_state}</span>
                        <svg className="w-3 h-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${color}`}>
                          {entry.to_state}
                        </span>
                        <span className="text-xs text-gray-400">{entry.action}</span>
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                        <span>{entry.timestamp}</span>
                        <span>by {entry.actor}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
