import { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import { useI18n } from '../i18n';

interface Message { id: string; role: 'user' | 'assistant'; text: string; agentName?: string; intent?: string; actionsTaken?: string[]; suggestions?: string[]; sources?: Array<{ entity: string; record_id: string; display: string; path: string[] }>; insights?: string[]; risks?: string[]; }
interface Agent { code: string; name: string; description: string; status: string; tasks_completed: number; success_rate: number; last_active: string; tools: string[]; }
interface CopilotResponse { response: string; agent: string; agent_name: string; intent: string; entities: string[]; actions_taken: string[]; suggestions: string[]; rule_ids_fired: string[]; compliant: boolean; sources: Array<{ entity: string; record_id: string; display: string; path: string[] }>; insights: string[]; risks: string[]; }
type Tab = 'chat' | 'agents' | 'activity' | 'tools';

const AGENT_COLORS: Record<string, string> = {
  executive_agent: 'from-blue-500 to-indigo-600',
  finance_agent: 'from-green-500 to-emerald-600',
  procurement_agent: 'from-purple-500 to-violet-600',
  project_agent: 'from-amber-500 to-orange-600',
  sales_agent: 'from-rose-500 to-pink-600',
  hr_agent: 'from-cyan-500 to-teal-600',
  operations_agent: 'from-slate-500 to-gray-600',
};

const AGENT_ICONS: Record<string, string> = {
  executive_agent: '👔',
  finance_agent: '💰',
  procurement_agent: '🛒',
  project_agent: '🏗',
  sales_agent: '📈',
  hr_agent: '👥',
  operations_agent: '⚙️',
};

const DEFAULT_AGENTS: Agent[] = [
  { code: 'executive_agent', name: 'Executive Agent', description: 'Business intelligence, KPI analysis, strategic insights', status: 'active', tasks_completed: 156, success_rate: 94, last_active: '2 min ago', tools: ['analytics', 'reports', 'search'] },
  { code: 'finance_agent', name: 'Finance Agent', description: 'Financial analysis, budgeting, accounting insights', status: 'active', tasks_completed: 234, success_rate: 97, last_active: '5 min ago', tools: ['ledger', 'reports', 'budgets'] },
  { code: 'procurement_agent', name: 'Procurement Agent', description: 'Supplier analysis, PO management, cost optimization', status: 'active', tasks_completed: 189, success_rate: 92, last_active: '1 min ago', tools: ['suppliers', 'orders', 'comparison'] },
  { code: 'project_agent', name: 'Project Agent', description: 'Project health, timeline, risk assessment', status: 'active', tasks_completed: 145, success_rate: 91, last_active: '10 min ago', tools: ['projects', 'timeline', 'risks'] },
  { code: 'sales_agent', name: 'Sales Agent', description: 'Customer analysis, pipeline, revenue forecasting', status: 'idle', tasks_completed: 98, success_rate: 89, last_active: '1 hour ago', tools: ['customers', 'pipeline', 'forecasts'] },
  { code: 'hr_agent', name: 'HR Agent', description: 'Employee analytics, attendance, performance', status: 'idle', tasks_completed: 67, success_rate: 95, last_active: '3 hours ago', tools: ['employees', 'attendance', 'performance'] },
  { code: 'operations_agent', name: 'Operations Agent', description: 'Operational efficiency, workflow monitoring', status: 'active', tasks_completed: 312, success_rate: 96, last_active: '30 sec ago', tools: ['workflows', 'monitoring', 'automation'] },
];

const SUGGESTIONS = [
  'What needs my approval today?',
  'Show me overdue invoices',
  'Project health summary',
  'Top suppliers by spend',
  'Budget utilization report',
  'Risk assessment for active projects',
];

const GREETING: Message = {
  id: 'greeting',
  role: 'assistant',
  text: "Welcome to the AI Workforce. I can connect you with specialized agents for executive, finance, procurement, project, sales, HR, and operations analysis. What would you like to know?",
  agentName: 'Executive Agent',
};

function uid(): string { return Math.random().toString(36).slice(2, 10); }

async function callCopilotApi(message: string, token: string): Promise<CopilotResponse> {
  return api<CopilotResponse>('/ai/copilot/chat', token, {
    method: 'POST',
    body: JSON.stringify({
      message,
      context: {
        include_approvals: true,
        include_projects: true,
        include_rules: true,
        include_events: true,
        include_suppliers: true,
      },
    }),
  });
}

function renderText(raw: string): React.ReactNode {
  const lines = raw.split('\n');
  return lines.map((line, li) => {
    const parts: React.ReactNode[] = [];
    const boldRe = /\*\*(.+?)\*\*/g;
    let m: RegExpExecArray | null;
    let lastIdx = 0;
    let key = 0;
    while ((m = boldRe.exec(line)) !== null) {
      if (m.index > lastIdx) parts.push(line.slice(lastIdx, m.index));
      parts.push(<strong key={key++}>{m[1]}</strong>);
      lastIdx = m.index + m[0].length;
    }
    if (lastIdx < line.length) parts.push(line.slice(lastIdx));
    if (line.startsWith('_') && line.endsWith('_')) return <p key={li} className="text-xs italic text-gray-400 mt-1">{line.slice(1, -1)}</p>;
    return <p key={li} className="leading-relaxed">{parts}</p>;
  });
}

export function AICopilotPage({ token }: { token: string }) {
  const { t } = useI18n();
  const [messages, setMessages] = useState<Message[]>([GREETING]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<Tab>('chat');
  const [agents] = useState<Agent[]>(DEFAULT_AGENTS);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading]);

  const send = async (text: string) => {
    if (!text.trim() || loading) return;
    const userMsg: Message = { id: uid(), role: 'user', text: text.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    const start = Date.now();
    try {
      const data = await callCopilotApi(text, token);
      const elapsed = Date.now() - start;
      if (elapsed < 400) await new Promise(r => setTimeout(r, 400 - elapsed));
      setMessages(prev => [...prev, {
        id: uid(),
        role: 'assistant',
        text: data.response,
        agentName: data.agent_name,
        intent: data.intent,
        actionsTaken: data.actions_taken,
        suggestions: data.suggestions,
        sources: data.sources,
        insights: data.insights,
        risks: data.risks,
      }]);
    } catch {
      setMessages(prev => [...prev, {
        id: uid(),
        role: 'assistant',
        text: t.aiCopilot.unableToReach,
        agentName: 'System',
      }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input); }
  };

  const totalTasks = agents.reduce((a, ag) => a + ag.tasks_completed, 0);
  const avgSuccess = Math.round(agents.reduce((a, ag) => a + ag.success_rate, 0) / agents.length);

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <header className="flex items-center gap-3 px-6 py-4 bg-white border-b border-gray-200 shadow-sm shrink-0">
        <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center text-white text-sm font-bold">AI</div>
        <div className="flex-1">
        <h1 className="text-lg font-semibold text-gray-900">{t.aiCopilot.title}</h1>
        <p className="text-xs text-gray-500">{agents.filter(a => a.status === 'active').length} {t.aiCopilot.agentsActive} &middot; {totalTasks} {t.aiCopilot.tasksCompleted}</p>
        </div>
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
          {(['chat', 'agents', 'activity', 'tools'] as const).map(tabKey => (
            <button key={tabKey} onClick={() => setTab(tabKey)} className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors capitalize ${tab === tabKey ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
              {tabKey === 'chat' ? t.aiCopilot.tabChat : tabKey === 'agents' ? t.aiCopilot.tabAgents : tabKey === 'activity' ? t.aiCopilot.tabActivity : t.aiCopilot.tabTools}
            </button>
          ))}
        </div>
      </header>

      {tab === 'chat' && (
        <>
          <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
            <div className="max-w-3xl mx-auto space-y-4">
              {messages.map(msg => (
                <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.role === 'assistant' && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold mr-2 mt-1">
                      {msg.agentName ? AGENT_ICONS[DEFAULT_AGENTS.find(a => a.name === msg.agentName)?.code || ''] || '🤖' : '🤖'}
                    </div>
                  )}
                  <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${msg.role === 'user' ? 'bg-blue-600 text-white rounded-br-md' : 'bg-white text-gray-800 border border-gray-200 shadow-sm rounded-bl-md'}`}>
                    {msg.agentName && (
                      <div className="flex items-center gap-2 mb-1">
                        <p className="text-xs font-medium text-blue-600">{msg.agentName}</p>
                        {msg.intent && (
                          <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-purple-100 text-purple-700 uppercase tracking-wide">{msg.intent}</span>
                        )}
                      </div>
                    )}
                    <div className={msg.role === 'user' ? 'text-white' : 'text-gray-800'}>{renderText(msg.text)}</div>
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-100">
                        <p className="text-xs font-medium text-gray-500 mb-1">{t.aiCopilot.sourcesLabel}</p>
                        <div className="flex flex-wrap gap-1">
                          {msg.sources.map((src, i) => (
                            <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-indigo-50 text-indigo-700 border border-indigo-200" title={src.path.join(' → ')}>
                              <span className="font-semibold">{src.entity}</span>
                              <span className="text-indigo-400">·</span>
                              <span>{src.display}</span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {msg.insights && msg.insights.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-100">
                        <p className="text-xs font-medium text-gray-500 mb-1">💡 {t.aiCopilot.insightsLabel}</p>
                        <ul className="list-disc list-inside space-y-0.5">
                          {msg.insights.map((insight, i) => (
                            <li key={i} className="text-xs text-gray-600">{insight}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {msg.risks && msg.risks.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-100">
                        <p className="text-xs font-medium text-gray-500 mb-1">⚠️ {t.aiCopilot.risksLabel}</p>
                        <ul className="list-disc list-inside space-y-0.5">
                          {msg.risks.map((risk, i) => (
                            <li key={i} className="text-xs text-red-600">{risk}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {msg.actionsTaken && msg.actionsTaken.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-100">
                        <p className="text-xs font-medium text-gray-500 mb-1">{t.aiCopilot.actionsTakenLabel}</p>
                        <div className="flex flex-wrap gap-1">
                          {msg.actionsTaken.map((action, i) => (
                            <span key={i} className="inline-block px-2 py-0.5 rounded text-[10px] font-mono bg-green-50 text-green-700">{action}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    {msg.suggestions && msg.suggestions.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-100">
                        <p className="text-xs font-medium text-gray-500 mb-1">{t.aiCopilot.suggestionsLabel}</p>
                        <div className="flex flex-wrap gap-1">
                          {msg.suggestions.map((sug, i) => (
                            <button key={i} onClick={() => send(sug)} className="inline-block px-2 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors">{sug}</button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold mr-2 mt-1">🤖</div>
                  <div className="bg-white border border-gray-200 shadow-sm rounded-2xl rounded-bl-md px-4 py-3">
                    <div className="flex items-center gap-1">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          </div>
          <div className="border-t border-gray-200 bg-white px-4 py-3 sm:px-6 shrink-0">
            <div className="max-w-3xl mx-auto">
              <div className="flex flex-wrap gap-2 mb-3">
                {SUGGESTIONS.map(s => (
                  <button key={s} onClick={() => send(s)} disabled={loading} className="px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-full hover:bg-blue-100 transition-colors disabled:opacity-50">{s}</button>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <input ref={inputRef} type="text" value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKey} placeholder={t.aiCopilot.chatPlaceholder} disabled={loading} className="flex-1 px-4 py-2.5 text-sm border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 bg-gray-50 disabled:opacity-50" />
                <button onClick={() => send(input)} disabled={!input.trim() || loading} className="flex items-center justify-center w-10 h-10 rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" /></svg>
                </button>
              </div>
            </div>
          </div>
        </>
      )}

      {tab === 'agents' && (
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-5xl mx-auto space-y-6">
            <div className="grid grid-cols-4 gap-4">
              {[
                ['Total Agents', agents.length, '🤖', 'text-blue-600'],
                [t.aiCopilot.activeNow, agents.filter(a => a.status === 'active').length, '🟢', 'text-green-600'],
                [t.aiCopilot.tasksCompletedStat, totalTasks, '📊', 'text-purple-600'],
                [t.aiCopilot.avgSuccessRate, `${avgSuccess}%`, '✅', 'text-indigo-600'],
              ].map(([label, value, icon, color]) => (
                <div key={label} className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                  <span className="text-2xl">{icon}</span>
                  <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
                  <p className="text-xs text-gray-500">{label as string}</p>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {agents.map(agent => (
                <div key={agent.code} className={`bg-white rounded-xl border border-gray-200 p-5 cursor-pointer hover:shadow-md transition-shadow ${selectedAgent === agent.code ? 'ring-2 ring-blue-400' : ''}`} onClick={() => setSelectedAgent(selectedAgent === agent.code ? null : agent.code)}>
                  <div className="flex items-start gap-4">
                    <div className={`w-12 h-12 bg-gradient-to-br ${AGENT_COLORS[agent.code] || 'from-gray-500 to-gray-600'} rounded-xl flex items-center justify-center text-white text-xl shrink-0`}>{AGENT_ICONS[agent.code] || '🤖'}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold text-gray-900">{agent.name}</h3>
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${agent.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>{agent.status}</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">{agent.description}</p>
                      <div className="flex items-center gap-4 mt-2">
                        <span className="text-xs text-gray-500">Tasks: <span className="font-medium text-gray-900">{agent.tasks_completed}</span></span>
                        <span className="text-xs text-gray-500">Success: <span className="font-medium text-green-600">{agent.success_rate}%</span></span>
                        <span className="text-xs text-gray-500">Active: <span className="font-medium text-gray-700">{agent.last_active}</span></span>
                      </div>
                    </div>
                  </div>
                  {selectedAgent === agent.code && (
                    <div className="mt-4 pt-4 border-t border-gray-100">
                      <p className="text-xs font-medium text-gray-500 mb-2">{t.aiCopilot.availableTools}</p>
                      <div className="flex flex-wrap gap-2">
                        {agent.tools.map(tool => (
                          <span key={tool} className="px-2 py-1 text-xs bg-blue-50 text-blue-700 rounded-md font-medium">{tool}</span>
                        ))}
                      </div>
                      <div className="mt-3 grid grid-cols-3 gap-2">
                        <div className="p-2 bg-gray-50 rounded-lg text-center"><p className="text-xs text-gray-500">Tasks</p><p className="text-sm font-bold text-gray-900">{agent.tasks_completed}</p></div>
                        <div className="p-2 bg-gray-50 rounded-lg text-center"><p className="text-xs text-gray-500">Success</p><p className="text-sm font-bold text-green-600">{agent.success_rate}%</p></div>
                        <div className="p-2 bg-gray-50 rounded-lg text-center"><p className="text-xs text-gray-500">Tools</p><p className="text-sm font-bold text-gray-900">{agent.tools.length}</p></div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === 'activity' && (
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-5xl mx-auto">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.aiCopilot.recentAiActivity}</h3>
              <div className="space-y-3">
                {[
                  { agent: 'Executive Agent', action: 'Generated project health report', time: '2 min ago', status: 'success' },
                  { agent: 'Finance Agent', action: 'Analyzed budget utilization for Project Alpha', time: '5 min ago', status: 'success' },
                  { agent: 'Procurement Agent', action: 'Compared supplier quotes for electrical materials', time: '12 min ago', status: 'success' },
                  { agent: 'Project Agent', action: 'Assessed risk for Project Omega', time: '18 min ago', status: 'success' },
                  { agent: 'Operations Agent', action: 'Monitored workflow bottleneck in approvals', time: '25 min ago', status: 'warning' },
                  { agent: 'Finance Agent', action: 'Generated cash flow forecast', time: '1 hour ago', status: 'success' },
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-4 py-3 border-b border-gray-100 last:border-0">
                    <div className={`w-10 h-10 bg-gradient-to-br ${AGENT_COLORS[DEFAULT_AGENTS.find(a => a.name === item.agent)?.code || ''] || 'from-gray-400 to-gray-500'} rounded-lg flex items-center justify-center text-white text-sm shrink-0`}>{AGENT_ICONS[DEFAULT_AGENTS.find(a => a.name === item.agent)?.code || ''] || '🤖'}</div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{item.agent}</p>
                      <p className="text-xs text-gray-500">{item.action}</p>
                    </div>
                    <div className="text-right">
                      <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${item.status === 'success' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>{item.status}</span>
                      <p className="text-xs text-gray-400 mt-1">{item.time}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === 'tools' && (
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-5xl mx-auto space-y-6">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.aiCopilot.aiToolRegistry}</h3>
              <p className="text-xs text-gray-500 mb-4">{t.aiCopilot.aiToolRegistryDesc}</p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {[
                  ['analytics', 'Analytics Engine', '📊', 'Query and analyze business data'],
                  ['search', 'Global Search', '🔍', 'Search across all entities'],
                  ['reports', 'Report Generator', '📈', 'Generate and run reports'],
                  ['notifications', 'Notification Service', '🔔', 'Send notifications to users'],
                  ['workflow', 'Workflow Engine', '⚡', 'Trigger and manage workflows'],
                  ['documents', 'Document Intelligence', '📄', 'OCR, classify, and extract data'],
                  ['ledger', 'Financial Ledger', '💰', 'Post and query financial entries'],
                  ['suppliers', 'Supplier Management', '🏭', 'Search and compare suppliers'],
                  ['projects', 'Project Management', '🏗', 'Access project data and status'],
                  ['automation', 'Automation Engine', '🤖', 'Execute automated business rules'],
                  ['integration', 'Integration Hub', '🔗', 'Connect to external systems'],
                  ['audit', 'Audit Trail', '🔍', 'Track and query audit events'],
                ].map(([code, name, icon, desc]) => (
                  <div key={code} className="p-4 bg-gray-50 rounded-xl">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xl">{icon}</span>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{name}</p>
                        <p className="text-xs text-gray-400 font-mono">{code}</p>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500">{desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
