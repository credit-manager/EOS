import { useState, useEffect } from 'react';
import { useI18n } from '../i18n';

interface BuilderObject {
  id: string; code: string; name: string; description?: string;
  object_type: string; is_system: boolean; is_active: boolean;
  fields?: BuilderField[]; rules?: BuilderRule[];
  workflows?: BuilderWorkflow[]; permissions?: BuilderPermission[];
}
interface BuilderRelation {
  id: string; code: string; name: string;
  source_object_id: string; target_object_id: string; relation_type: string;
}
interface BuilderWorkflow {
  id: string; code: string; name: string;
  object_id: string; trigger_type: string; is_active: boolean;
}
interface BuilderAutomation {
  id: string; code: string; name: string;
  trigger_type: string; is_active: boolean; run_count: number;
}
interface BuilderField {
  id: string; code: string; name: string;
  field_type: string; required: boolean; unique: boolean;
}
interface BuilderRule {
  id: string; event: string; condition: string; action: string;
  object_id?: string; is_active?: boolean;
}
interface BuilderPermission {
  role: string; create: boolean; read: boolean;
  update: boolean; delete: boolean; approve: boolean;
}

type WizardStep = 'basic' | 'fields' | 'relations' | 'rules' | 'workflow' | 'permissions' | 'review';

const FIELD_TYPES = ['text', 'number', 'date', 'boolean', 'enum', 'json', 'file'];
const RELATION_TYPES = ['one-to-one', 'one-to-many', 'many-to-many'];
const TRIGGER_EVENTS = ['on_create', 'on_update', 'on_delete', 'on_status_change', 'on_schedule'];
const CONDITIONS = ['always', 'field_equals', 'field_contains', 'status_equals', 'custom_expression'];
const ACTIONS = ['create_record', 'update_record', 'send_notification', 'call_webhook', 'update_status', 'log_audit', 'send_email', 'trigger_workflow'];
const ROLES = ['admin', 'manager', 'user', 'viewer'] as const;
const PERM_ACTIONS = ['create', 'read', 'update', 'delete', 'approve'] as const;

const WIZARD_STEPS: { key: WizardStep; labelKey: string; icon: string }[] = [
  { key: 'basic', labelKey: 'wizardBasicInfo', icon: '📝' },
  { key: 'fields', labelKey: 'wizardFields', icon: '📋' },
  { key: 'relations', labelKey: 'wizardRelationships', icon: '🔗' },
  { key: 'rules', labelKey: 'wizardRules', icon: '⚖️' },
  { key: 'workflow', labelKey: 'wizardWorkflow', icon: '🔄' },
  { key: 'permissions', labelKey: 'wizardPermissions', icon: '🔐' },
  { key: 'review', labelKey: 'wizardReview', icon: '✅' },
];

const initialPerms = (): Record<string, Record<string, boolean>> =>
  Object.fromEntries(ROLES.map(r => [r, Object.fromEntries(PERM_ACTIONS.map(a => [a, r === 'admin']))]));

export default function BuilderPage({ token }: { token: string }) {
  const { t } = useI18n();
  const [tab, setTab] = useState<'objects' | 'relations' | 'workflows' | 'automations' | 'rules' | 'permissions'>('objects');
  const [objects, setObjects] = useState<BuilderObject[]>([]);
  const [relations, setRelations] = useState<BuilderRelation[]>([]);
  const [workflows, setWorkflows] = useState<BuilderWorkflow[]>([]);
  const [automations, setAutomations] = useState<BuilderAutomation[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [wizardStep, setWizardStep] = useState<WizardStep>('basic');
  const [showGenerate, setShowGenerate] = useState<BuilderObject | null>(null);

  const [form, setForm] = useState({ code: '', name: '', object_type: 'entity', description: '' });
  const [formFields, setFormFields] = useState<BuilderField[]>([]);
  const [formRelations, setFormRelations] = useState<{ name: string; target_code: string; relation_type: string }[]>([]);
  const [formRules, setFormRules] = useState<{ event: string; condition: string; action: string }[]>([]);
  const [formWorkflow, setFormWorkflow] = useState({ trigger_type: 'on_create', transitions: ['draft', 'pending', 'approved', 'rejected'] });
  const [formPermissions, setFormPermissions] = useState<Record<string, Record<string, boolean>>>(initialPerms);

  const [fieldForm, setFieldForm] = useState({ code: '', name: '', field_type: 'text', required: false, unique: false });
  const [ruleForm, setRuleForm] = useState({ event: 'on_create', condition: 'always', action: 'create_record' });
  const [relForm, setRelForm] = useState({ name: '', target_code: '', relation_type: 'one-to-many' });

  useEffect(() => {
    Promise.all([
      fetch('/api/v1/builder/objects', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      fetch('/api/v1/builder/relations', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      fetch('/api/v1/builder/workflows', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      fetch('/api/v1/builder/automations', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
    ]).then(([o, r, w, a]) => {
      setObjects(o); setRelations(r); setWorkflows(w); setAutomations(a);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [token]);

  const resetWizard = () => {
    setWizardStep('basic');
    setForm({ code: '', name: '', object_type: 'entity', description: '' });
    setFormFields([]); setFormRelations([]); setFormRules([]);
    setFormWorkflow({ trigger_type: 'on_create', transitions: ['draft', 'pending', 'approved', 'rejected'] });
    setFormPermissions(initialPerms());
  };

  const handleCreate = async () => {
    const r = await fetch('/api/v1/builder/objects', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...form, fields: formFields, relations: formRelations, rules: formRules, workflow: formWorkflow, permissions: formPermissions }),
    });
    if (r.ok) {
      const created = await r.json();
      const newObj: BuilderObject = {
        ...created, fields: formFields, rules: formRules,
        workflows: [{ id: `wf_${Date.now()}`, code: form.code + '_wf', name: form.name + ' Workflow', object_id: created.id, trigger_type: formWorkflow.trigger_type, is_active: true }],
      };
      setObjects(prev => [...prev, newObj]);
      setShowCreate(false); resetWizard();
    }
  };

  const handleDeleteObject = async (id: string) => {
    if (!confirm(t.builderPage.deleteConfirm)) return;
    const r = await fetch(`/api/v1/builder/objects/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
    if (r.ok) setObjects(prev => prev.filter(o => o.id !== id));
  };

  const addObjectField = () => {
    if (!fieldForm.code || !fieldForm.name) return;
    setFormFields(prev => [...prev, { id: `f_${Date.now()}`, ...fieldForm }]);
    setFieldForm({ code: '', name: '', field_type: 'text', required: false, unique: false });
  };

  const addObjectRelation = () => {
    if (!relForm.name) return;
    setFormRelations(prev => [...prev, { ...relForm }]);
    setRelForm({ name: '', target_code: '', relation_type: 'one-to-many' });
  };

  const addObjectRule = () => {
    setFormRules(prev => [...prev, { ...ruleForm }]);
    setRuleForm({ event: 'on_create', condition: 'always', action: 'create_record' });
  };

  const togglePerm = (role: string, action: string) => {
    setFormPermissions(prev => ({ ...prev, [role]: { ...prev[role], [action]: !prev[role][action] } }));
  };

  const getObjectStats = (obj: BuilderObject) => ({
    fields: obj.fields?.length || 0,
    relations: relations.filter(r => r.source_object_id === obj.id || r.target_object_id === obj.id).length,
    rules: obj.rules?.length || 0,
    workflows: obj.workflows?.length || workflows.filter(w => w.object_id === obj.id).length,
  });

  const stepIdx = WIZARD_STEPS.findIndex(s => s.key === wizardStep);

  if (loading) return <div className="flex items-center justify-center h-64"><p className="text-gray-500">{t.builderPage.loadingBuilder}</p></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{t.builderPage.eosBuilder}</h2>
          <p className="text-sm text-gray-500">{t.builderPage.subtitle}</p>
        </div>
        {tab === 'objects' && (
          <button onClick={() => { resetWizard(); setShowCreate(true); }} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            {t.builderPage.newObject}
          </button>
        )}
      </div>

      <div className="flex gap-2 border-b border-gray-200 overflow-x-auto">
        {([
          ['objects', `${t.builderPage.objects} (${objects.length})`],
          ['relations', `${t.builderPage.relations} (${relations.length})`],
          ['workflows', `${t.builderPage.workflows} (${workflows.length})`],
          ['automations', `${t.builderPage.automations} (${automations.length})`],
          ['rules', `${t.builderPage.rules} (${objects.reduce((s, o) => s + (o.rules?.length || 0), 0)})`],
          ['permissions', t.builderPage.permissions],
        ] as const).map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${tab === key ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {label}
          </button>
        ))}
      </div>

      {tab === 'objects' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {objects.map(obj => {
            const stats = getObjectStats(obj);
            return (
              <div key={obj.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center text-lg">📦</div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 truncate">{obj.name}</h3>
                    <p className="text-xs text-gray-500 font-mono">{obj.code}</p>
                  </div>
                </div>
                <p className="text-sm text-gray-600 mb-3 line-clamp-2">{obj.description || t.builderPage.noDescription}</p>
                <div className="flex gap-1.5 flex-wrap mb-3">
                  <span className="px-2 py-0.5 bg-gray-100 rounded text-gray-600 text-xs">{obj.object_type}</span>
                  {obj.is_system && <span className="px-2 py-0.5 bg-blue-50 text-blue-600 rounded text-xs">{t.builderPage.system}</span>}
                </div>
                <div className="flex gap-3 text-xs text-gray-500 mb-3">
                  <span>{stats.fields} fields</span>
                  <span>{stats.relations} relations</span>
                  <span>{stats.rules} rules</span>
                  <span>{stats.workflows} workflows</span>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => { resetWizard(); setForm({ code: obj.code, name: obj.name, object_type: obj.object_type, description: obj.description || '' }); setShowCreate(true); }}
                    className="flex-1 px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">{t.builderPage.edit}</button>
                  <button onClick={() => setShowGenerate(obj)}
                    className="flex-1 px-3 py-1.5 text-xs bg-indigo-100 text-indigo-700 rounded-lg hover:bg-indigo-200">{t.builderPage.generate}</button>
                  {!obj.is_system && (
                    <button onClick={() => handleDeleteObject(obj.id)}
                      className="px-3 py-1.5 text-xs bg-red-50 text-red-600 rounded-lg hover:bg-red-100">{t.builderPage.del}</button>
                  )}
                </div>
              </div>
            );
          })}
          {objects.length === 0 && (
            <div className="col-span-full text-center py-12 text-gray-400">
              <div className="text-4xl mb-2">🏗️</div>
              <p className="text-lg font-medium">{t.builderPage.noObjects}</p>
              <p className="text-sm">{t.builderPage.noObjectsHint}</p>
            </div>
          )}
        </div>
      )}

      {tab === 'relations' && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b"><tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.builderPage.nameLabel}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.builderPage.typeLabel}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.builderPage.codeLabel}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.builderPage.codeLabel}</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-200">
              {relations.map(r => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{r.name}</td>
                  <td className="px-4 py-3"><span className="px-2 py-0.5 bg-purple-50 text-purple-600 rounded text-xs">{r.relation_type}</span></td>
                  <td className="px-4 py-3 text-sm font-mono text-gray-600">{r.source_object_id.slice(0, 8)}</td>
                  <td className="px-4 py-3 text-sm font-mono text-gray-600">{r.target_object_id.slice(0, 8)}</td>
                </tr>
              ))}
              {relations.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">{t.builderPage.noRelationsDefined}</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'workflows' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {workflows.map(w => (
            <div key={w.id} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">{w.name}</h3>
                  <p className="text-sm text-gray-500">{w.code}</p>
                </div>
                <span className="px-2 py-0.5 rounded text-xs bg-green-100 text-green-700">{w.trigger_type}</span>
              </div>
            </div>
          ))}
          {workflows.length === 0 && <p className="text-center text-gray-400 py-8 col-span-2">{t.builderPage.noWorkflowsDefined}</p>}
        </div>
      )}

      {tab === 'automations' && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b"><tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.builderPage.nameLabel}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.builderPage.trigger}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.builderPage.runs}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.builderPage.statusLabel}</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-200">
              {automations.map(a => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{a.name}</td>
                  <td className="px-4 py-3"><span className="px-2 py-0.5 bg-orange-50 text-orange-600 rounded text-xs">{a.trigger_type}</span></td>
                  <td className="px-4 py-3 text-sm text-gray-600">{a.run_count}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${a.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {a.is_active ? t.builderPage.active : t.builderPage.inactive}
                    </span>
                  </td>
                </tr>
              ))}
              {automations.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">{t.builderPage.noAutomationsDefined}</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'rules' && (
        <div className="space-y-4">
          {objects.filter(o => o.rules && o.rules.length > 0).map(obj => (
            <div key={obj.id} className="bg-white rounded-xl border border-gray-200 p-4">
              <h3 className="font-semibold text-gray-900 mb-3">{obj.name} — {t.builderPage.rules}</h3>
              <div className="space-y-2">
                {obj.rules!.map((rule, i) => (
                  <div key={rule.id || i} className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg text-sm font-mono flex-wrap">
                    <span className="text-blue-600 font-bold">WHEN</span>
                    <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded">{rule.event}</span>
                    <span className="text-amber-600 font-bold">IF</span>
                    <span className="px-2 py-0.5 bg-amber-50 text-amber-700 rounded">{rule.condition}</span>
                    <span className="text-green-600 font-bold">THEN</span>
                    <span className="px-2 py-0.5 bg-green-50 text-green-700 rounded">{rule.action}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
          {objects.every(o => !o.rules || o.rules.length === 0) && (
            <div className="text-center py-12 text-gray-400">
              <div className="text-4xl mb-2">⚖️</div>
              <p className="text-lg font-medium">{t.builderPage.noRulesDefined}</p>
              <p className="text-sm">{t.builderPage.noRulesHint}</p>
            </div>
          )}
        </div>
      )}

      {tab === 'permissions' && (
        <div className="space-y-4">
          {objects.map(obj => (
            <div key={obj.id} className="bg-white rounded-xl border border-gray-200 p-4">
              <h3 className="font-semibold text-gray-900 mb-3">{obj.name} — {t.builderPage.permissions}</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                          <th className="px-4 py-2 text-left font-medium text-gray-500">{t.builderPage.role}</th>
                      {PERM_ACTIONS.map(a => (
                        <th key={a} className="px-4 py-2 text-center font-medium text-gray-500 capitalize">{a}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {ROLES.map(role => (
                      <tr key={role} className="border-b last:border-0">
                        <td className="px-4 py-2 font-medium text-gray-900 capitalize">{role}</td>
                        {PERM_ACTIONS.map(action => {
                          const has = obj.permissions?.find((p: BuilderPermission) => p.role === role)?.[action as keyof BuilderPermission] ?? (role === 'admin');
                          return (
                            <td key={action} className="px-4 py-2 text-center">
                              <div className={`w-8 h-5 mx-auto rounded-full cursor-pointer transition-colors ${has ? 'bg-blue-600' : 'bg-gray-300'}`}
                                title={`${role} ${action}: ${has ? 'Yes' : 'No'}`}>
                                <div className={`w-4 h-4 bg-white rounded-full shadow transform transition-transform mt-0.5 ${has ? 'translate-x-3.5' : 'translate-x-0.5'}`} />
                              </div>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
          {objects.length === 0 && (
            <div className="text-center py-12 text-gray-400">
              <div className="text-4xl mb-2">🔐</div>
              <p className="text-lg font-medium">{t.builderPage.noObjectsToConfigure}</p>
              <p className="text-sm">{t.builderPage.noObjectsHintPermissions}</p>
            </div>
          )}
        </div>
      )}

      {showGenerate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowGenerate(null)}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg p-6" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold">{t.builderPage.generateTitle} {showGenerate.name}</h3>
              <button onClick={() => setShowGenerate(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>
            <p className="text-sm text-gray-500 mb-4">{t.builderPage.generateDesc}</p>
            <div className="space-y-2">
              {[
                { icon: '🗄️', name: t.builderPage.databaseTable, desc: `Table \`${showGenerate.code}\` with all fields, indexes, and constraints` },
                { icon: '🔌', name: t.builderPage.apiEndpoints, desc: `Full CRUD: GET /${showGenerate.code}, POST, PUT, DELETE` },
                { icon: '📝', name: t.builderPage.uiForms, desc: 'Auto-generated create/edit forms with field validation' },
                { icon: '🔐', name: t.builderPage.permissionsGen, desc: 'Role-based access control (admin, manager, user, viewer)' },
                { icon: '🔄', name: t.builderPage.workflowGen, desc: 'State machine with transitions and approval flows' },
                { icon: '📋', name: t.builderPage.auditTrail, desc: 'Automatic change tracking with diff snapshots' },
                { icon: '🔍', name: t.builderPage.searchIndex, desc: 'Full-text search and filter capabilities' },
                { icon: '🤖', name: t.builderPage.aiContext, desc: 'AI-readable schema for intelligent suggestions' },
              ].map((item, i) => (
                <div key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                  <span className="text-xl mt-0.5">{item.icon}</span>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{item.name}</p>
                    <p className="text-xs text-gray-500">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex gap-3 justify-end mt-6">
              <button onClick={() => setShowGenerate(null)} className="px-4 py-2 text-gray-600 hover:text-gray-800">{t.common.cancel}</button>
              <button onClick={() => { alert(`Generating artifacts for "${showGenerate.code}"...`); setShowGenerate(null); }}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">{t.builderPage.generateAll}</button>
            </div>
          </div>
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => { setShowCreate(false); resetWizard(); }}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold">{t.builderPage.createBusinessObject}</h3>
                <button onClick={() => { setShowCreate(false); resetWizard(); }} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
              </div>
              <div className="flex gap-1">
                {WIZARD_STEPS.map((step, i) => (
                  <div key={step.key} className="flex items-center flex-1">
                    <div className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium cursor-pointer transition-colors
                      ${wizardStep === step.key ? 'bg-blue-100 text-blue-700' : i < stepIdx ? 'bg-green-50 text-green-600' : 'bg-gray-50 text-gray-400'}`}
                      onClick={() => i <= stepIdx && setWizardStep(step.key)}>
                      <span>{step.icon}</span>
                       <span className="hidden sm:inline">{t.builderPage[step.labelKey as keyof typeof t.builderPage]}</span>
                    </div>
                    {i < WIZARD_STEPS.length - 1 && <div className={`w-4 h-px mx-0.5 ${i < stepIdx ? 'bg-green-300' : 'bg-gray-200'}`} />}
                  </div>
                ))}
              </div>
            </div>

            <div className="p-6">
              {wizardStep === 'basic' && (
                <div className="space-y-4">
                  <h4 className="font-semibold text-gray-900">{t.builderPage.basicInformation}</h4>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">{t.builderPage.codeLabel}</label>
                    <input placeholder="e.g. fleet_vehicle" value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))}
                      className="w-full px-4 py-2 border rounded-lg font-mono text-sm" />
                    <p className="text-xs text-gray-400 mt-1">{t.builderPage.codeHint}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">{t.builderPage.nameLabel}</label>
                    <input placeholder="e.g. Fleet Vehicle" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                      className="w-full px-4 py-2 border rounded-lg text-sm" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">{t.builderPage.typeLabel}</label>
                    <select value={form.object_type} onChange={e => setForm(f => ({ ...f, object_type: e.target.value }))}
                      className="w-full px-4 py-2 border rounded-lg text-sm">
                      <option value="entity">{t.builderPage.entityType}</option>
                      <option value="document">{t.builderPage.documentType}</option>
                      <option value="transaction">{t.builderPage.transactionType}</option>
                      <option value="reference">{t.builderPage.referenceType}</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">{t.builderPage.descriptionLabel}</label>
                    <textarea placeholder={t.builderPage.descriptionPlaceholder} value={form.description}
                      onChange={e => setForm(f => ({ ...f, description: e.target.value }))} className="w-full px-4 py-2 border rounded-lg text-sm" rows={2} />
                  </div>
                </div>
              )}

              {wizardStep === 'fields' && (
                <div className="space-y-4">
                  <h4 className="font-semibold text-gray-900">{t.builderPage.defineFields}</h4>
                  {formFields.length > 0 && (
                    <div className="space-y-1">
                      {formFields.map(f => (
                        <div key={f.id} className="flex items-center gap-3 p-2 bg-gray-50 rounded text-sm">
                          <span className="font-mono font-medium text-gray-900 w-32 truncate">{f.code}</span>
                          <span className="text-gray-500">{f.name}</span>
                          <span className="px-1.5 py-0.5 bg-gray-200 rounded text-xs">{f.field_type}</span>
                          {f.required && <span className="px-1.5 py-0.5 bg-red-50 text-red-600 rounded text-xs">required</span>}
                          {f.unique && <span className="px-1.5 py-0.5 bg-purple-50 text-purple-600 rounded text-xs">unique</span>}
                          <button onClick={() => setFormFields(prev => prev.filter(x => x.id !== f.id))} className="ml-auto text-gray-400 hover:text-red-500 text-xs">x</button>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="border border-dashed border-gray-300 rounded-lg p-3 space-y-3">
                    <p className="text-xs text-gray-500 font-medium">{t.builderPage.addField}</p>
                    <div className="grid grid-cols-2 gap-3">
                      <input placeholder="Code (e.g. plate_number)" value={fieldForm.code} onChange={e => setFieldForm(f => ({ ...f, code: e.target.value }))}
                        className="px-3 py-1.5 border rounded-lg text-sm font-mono" />
                      <input placeholder="Name (e.g. Plate Number)" value={fieldForm.name} onChange={e => setFieldForm(f => ({ ...f, name: e.target.value }))}
                        className="px-3 py-1.5 border rounded-lg text-sm" />
                    </div>
                    <div className="grid grid-cols-3 gap-3 items-center">
                      <select value={fieldForm.field_type} onChange={e => setFieldForm(f => ({ ...f, field_type: e.target.value }))}
                        className="px-3 py-1.5 border rounded-lg text-sm">
                        {FIELD_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                      </select>
                      <label className="flex items-center gap-1.5 text-sm">
                        <input type="checkbox" checked={fieldForm.required} onChange={e => setFieldForm(f => ({ ...f, required: e.target.checked }))} className="rounded" />
                        {t.builderPage.required}
                      </label>
                      <label className="flex items-center gap-1.5 text-sm">
                        <input type="checkbox" checked={fieldForm.unique} onChange={e => setFieldForm(f => ({ ...f, unique: e.target.checked }))} className="rounded" />
                        {t.builderPage.unique}
                      </label>
                    </div>
                    <button onClick={addObjectField} disabled={!fieldForm.code || !fieldForm.name}
                      className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
                      {t.builderPage.addFieldBtn}
                    </button>
                  </div>
                </div>
              )}

              {wizardStep === 'relations' && (
                <div className="space-y-4">
                  <h4 className="font-semibold text-gray-900">{t.builderPage.defineRelationships}</h4>
                  {formRelations.length > 0 && (
                    <div className="space-y-1">
                      {formRelations.map((r, i) => (
                        <div key={i} className="flex items-center gap-3 p-2 bg-gray-50 rounded text-sm">
                          <span className="font-medium text-gray-900">{r.name || 'Unnamed'}</span>
                          <span className="px-1.5 py-0.5 bg-purple-50 text-purple-600 rounded text-xs">{r.relation_type}</span>
                          <span className="text-gray-500">→ {r.target_code || '...'}</span>
                          <button onClick={() => setFormRelations(prev => prev.filter((_, idx) => idx !== i))} className="ml-auto text-gray-400 hover:text-red-500 text-xs">x</button>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="border border-dashed border-gray-300 rounded-lg p-3 space-y-3">
                    <p className="text-xs text-gray-500 font-medium">{t.builderPage.addRelationship}</p>
                    <div className="grid grid-cols-2 gap-3">
                      <input placeholder="Relation name" value={relForm.name} onChange={e => setRelForm(f => ({ ...f, name: e.target.value }))}
                        className="px-3 py-1.5 border rounded-lg text-sm" />
                      <input placeholder="Target object code" value={relForm.target_code} onChange={e => setRelForm(f => ({ ...f, target_code: e.target.value }))}
                        className="px-3 py-1.5 border rounded-lg text-sm font-mono" />
                    </div>
                    <select value={relForm.relation_type} onChange={e => setRelForm(f => ({ ...f, relation_type: e.target.value }))}
                      className="px-3 py-1.5 border rounded-lg text-sm">
                      {RELATION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                    <button onClick={addObjectRelation} disabled={!relForm.name}
                      className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
                      {t.builderPage.addRelationBtn}
                    </button>
                  </div>
                </div>
              )}

              {wizardStep === 'rules' && (
                <div className="space-y-4">
                  <h4 className="font-semibold text-gray-900">{t.builderPage.defineRules}</h4>
                  <p className="text-xs text-gray-500">{t.builderPage.rulesPatternHint}</p>
                  {formRules.length > 0 && (
                    <div className="space-y-2">
                      {formRules.map((r, i) => (
                        <div key={i} className="flex items-center gap-2 p-2 bg-gray-50 rounded text-sm font-mono">
                    <span className="text-blue-600 font-bold">{t.builderPage.when}</span>
                          <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded">{r.event}</span>
                    <span className="text-amber-600 font-bold">{t.builderPage.if}</span>
                          <span className="px-1.5 py-0.5 bg-amber-50 text-amber-700 rounded">{r.condition}</span>
                    <span className="text-green-600 font-bold">{t.builderPage.then}</span>
                          <span className="px-1.5 py-0.5 bg-green-50 text-green-700 rounded">{r.action}</span>
                          <button onClick={() => setFormRules(prev => prev.filter((_, idx) => idx !== i))} className="ml-auto text-gray-400 hover:text-red-500 text-xs">x</button>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="border border-dashed border-gray-300 rounded-lg p-3 space-y-3">
                    <p className="text-xs text-gray-500 font-medium">{t.builderPage.addRule}</p>
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">{t.builderPage.when} (event)</label>
                        <select value={ruleForm.event} onChange={e => setRuleForm(f => ({ ...f, event: e.target.value }))}
                          className="w-full px-3 py-1.5 border rounded-lg text-sm">
                          {TRIGGER_EVENTS.map(e => <option key={e} value={e}>{e}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">{t.builderPage.if} (condition)</label>
                        <select value={ruleForm.condition} onChange={e => setRuleForm(f => ({ ...f, condition: e.target.value }))}
                          className="w-full px-3 py-1.5 border rounded-lg text-sm">
                          {CONDITIONS.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">{t.builderPage.then} (action)</label>
                        <select value={ruleForm.action} onChange={e => setRuleForm(f => ({ ...f, action: e.target.value }))}
                          className="w-full px-3 py-1.5 border rounded-lg text-sm">
                          {ACTIONS.map(a => <option key={a} value={a}>{a}</option>)}
                        </select>
                      </div>
                    </div>
                    <button onClick={addObjectRule}
                      className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
                      {t.builderPage.addRule}
                    </button>
                  </div>
                </div>
              )}

              {wizardStep === 'workflow' && (
                <div className="space-y-4">
                  <h4 className="font-semibold text-gray-900">{t.builderPage.defineWorkflow}</h4>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">{t.builderPage.triggerType}</label>
                    <select value={formWorkflow.trigger_type} onChange={e => setFormWorkflow(f => ({ ...f, trigger_type: e.target.value }))}
                      className="w-full px-4 py-2 border rounded-lg text-sm">
                      <option value="on_create">On Create</option>
                      <option value="on_update">On Update</option>
                      <option value="on_status_change">On Status Change</option>
                      <option value="on_schedule">On Schedule</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">{t.builderPage.workflowStates}</label>
                    <div className="flex flex-wrap gap-2">
                      {formWorkflow.transitions.map((s, i) => (
                        <span key={i} className="inline-flex items-center gap-1 px-3 py-1 bg-green-50 text-green-700 rounded-full text-sm">
                          {s}
                          <button onClick={() => setFormWorkflow(f => ({ ...f, transitions: f.transitions.filter((_, idx) => idx !== i) }))}
                            className="text-green-500 hover:text-green-700 text-xs ml-1">&times;</button>
                        </span>
                      ))}
                    </div>
                    <div className="flex gap-2 mt-2">
                      <input placeholder={t.builderPage.addState} className="px-3 py-1.5 border rounded-lg text-sm flex-1"
                        onKeyDown={e => {
                          if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                            setFormWorkflow(f => ({ ...f, transitions: [...f.transitions, e.currentTarget.value.trim()] }));
                            e.currentTarget.value = '';
                          }
                        }} />
                    </div>
                    <p className="text-xs text-gray-400 mt-1">{t.builderPage.workflowHint}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">{t.builderPage.visualFlow}</label>
                    <div className="flex items-center gap-1 flex-wrap p-3 bg-gray-50 rounded-lg">
                      {formWorkflow.transitions.map((s, i) => (
                        <span key={i} className="flex items-center gap-1">
                          <span className="px-3 py-1 bg-white border rounded-lg text-sm font-medium text-gray-700">{s}</span>
                          {i < formWorkflow.transitions.length - 1 && <span className="text-gray-400">→</span>}
                        </span>
                      ))}
                      {formWorkflow.transitions.length === 0 && <span className="text-gray-400 text-sm">{t.builderPage.noStatesDefined}</span>}
                    </div>
                  </div>
                </div>
              )}

              {wizardStep === 'permissions' && (
                <div className="space-y-4">
                  <h4 className="font-semibold text-gray-900">{t.builderPage.setPermissions}</h4>
                  <p className="text-xs text-gray-500">{t.builderPage.permissionsHint}</p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="px-4 py-2 text-left font-medium text-gray-500">{t.builderPage.role}</th>
                          {PERM_ACTIONS.map(a => (
                            <th key={a} className="px-4 py-2 text-center font-medium text-gray-500 capitalize">{a}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {ROLES.map(role => (
                          <tr key={role} className="border-b last:border-0">
                            <td className="px-4 py-2 font-medium text-gray-900 capitalize">{role}</td>
                            {PERM_ACTIONS.map(action => (
                              <td key={action} className="px-4 py-2 text-center">
                                <div onClick={() => togglePerm(role, action)}
                                  className={`w-10 h-5 mx-auto rounded-full cursor-pointer transition-colors ${formPermissions[role]?.[action] ? 'bg-blue-600' : 'bg-gray-300'}`}>
                                  <div className={`w-4 h-4 bg-white rounded-full shadow transform transition-transform mt-0.5 ${formPermissions[role]?.[action] ? 'translate-x-5' : 'translate-x-0.5'}`} />
                                </div>
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {wizardStep === 'review' && (
                <div className="space-y-4">
                  <h4 className="font-semibold text-gray-900">{t.builderPage.reviewAndCreate}</h4>
                  <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center text-lg">📦</div>
                      <div>
                        <h5 className="font-semibold text-gray-900">{form.name || t.builderPage.unnamed}</h5>
                        <p className="text-xs text-gray-500 font-mono">{form.code}</p>
                      </div>
                    </div>
                    <p className="text-sm text-gray-600">{form.description || t.builderPage.noDescription}</p>
                    <div className="flex gap-1.5 flex-wrap">
                      <span className="px-2 py-0.5 bg-gray-200 rounded text-xs">{form.object_type}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div className="p-3 bg-white rounded-lg border">
                        <p className="text-gray-500 text-xs mb-1">Fields</p>
                        <p className="font-semibold text-gray-900">{formFields.length}</p>
                        {formFields.map(f => <p key={f.id} className="text-xs text-gray-500 font-mono">{f.code}: {f.field_type}</p>)}
                      </div>
                      <div className="p-3 bg-white rounded-lg border">
                        <p className="text-gray-500 text-xs mb-1">Relationships</p>
                        <p className="font-semibold text-gray-900">{formRelations.length}</p>
                        {formRelations.map((r, i) => <p key={i} className="text-xs text-gray-500">{r.name} → {r.target_code}</p>)}
                      </div>
                      <div className="p-3 bg-white rounded-lg border">
                        <p className="text-gray-500 text-xs mb-1">Rules</p>
                        <p className="font-semibold text-gray-900">{formRules.length}</p>
                        {formRules.map((r, i) => <p key={i} className="text-xs text-gray-500 font-mono">{r.event} → {r.action}</p>)}
                      </div>
                      <div className="p-3 bg-white rounded-lg border">
                        <p className="text-gray-500 text-xs mb-1">Workflow</p>
                        <p className="font-semibold text-gray-900">{formWorkflow.transitions.length} states</p>
                        <p className="text-xs text-gray-500">{formWorkflow.transitions.join(' → ')}</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-indigo-50 rounded-lg p-3">
                    <p className="text-sm font-medium text-indigo-900 mb-1">{t.builderPage.willGenerate}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {[t.builderPage.databaseTable, t.builderPage.apiEndpoints, t.builderPage.uiForms, t.builderPage.permissionsGen, t.builderPage.workflowGen, t.builderPage.auditTrail, t.builderPage.searchIndex, t.builderPage.aiContext].map(a => (
                        <span key={a} className="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded text-xs">{a}</span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="p-6 border-t border-gray-200 flex justify-between">
              <button onClick={() => {
                const prevIdx = WIZARD_STEPS.findIndex(s => s.key === wizardStep) - 1;
                if (prevIdx >= 0) setWizardStep(WIZARD_STEPS[prevIdx].key);
              }} disabled={stepIdx === 0}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 disabled:opacity-30 disabled:cursor-not-allowed">
                {t.builderPage.back}
              </button>
              <div className="flex gap-3">
                <button onClick={() => { setShowCreate(false); resetWizard(); }}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800">{t.builderPage.cancel}</button>
                {stepIdx < WIZARD_STEPS.length - 1 ? (
                  <button onClick={() => setWizardStep(WIZARD_STEPS[stepIdx + 1].key)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                    {t.builderPage.next}
                  </button>
                ) : (
                  <button onClick={handleCreate} disabled={!form.code || !form.name}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">
                    {t.builderPage.createObject}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
