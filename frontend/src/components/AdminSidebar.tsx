import React from 'react';
import { useI18n } from '../i18n';
import { TranslationKeys } from '../i18n';

interface NavGroup {
  title: string;
  items: { id: string; label: string; icon: string }[];
}

function getNavGroups(userRole: string, t: TranslationKeys): NavGroup[] {
  const base: NavGroup[] = [
    { title: t.adminSidebar.groupOrganization, items: [
      { id: 'tenants', label: t.adminSidebar.tenants, icon: '🏢' },
      { id: 'users', label: t.adminSidebar.users, icon: '👥' },
      { id: 'roles', label: t.adminSidebar.rolesPermissions, icon: '🔐' },
    ]},
    { title: t.adminSidebar.groupCommerce, items: [
      { id: 'plans', label: t.adminSidebar.plans, icon: '💳' },
      { id: 'subscriptions', label: t.adminSidebar.subscriptions, icon: '📋' },
      { id: 'billing', label: t.adminSidebar.billing, icon: '💰' },
      { id: 'transactions', label: t.adminSidebar.transactions, icon: '💵' },
    ]},
    { title: t.adminSidebar.groupPlatform, items: [
      { id: 'applications', label: t.adminSidebar.applications, icon: '📱' },
      { id: 'feature-flags', label: t.adminSidebar.featureFlags, icon: '⚡' },
      { id: 'integrations', label: t.adminSidebar.integrationsHub, icon: '🔗' },
      { id: 'api', label: t.adminSidebar.apiManagement, icon: '🔑' },
    ]},
    { title: t.adminSidebar.groupAi, items: [
      { id: 'ai-control', label: t.adminSidebar.aiControlCenter, icon: '🧠' },
      { id: 'ai-models', label: t.adminSidebar.aiModels, icon: '🤖' },
      { id: 'ai-workforce', label: t.adminSidebar.aiWorkforce, icon: '👨‍💻' },
      { id: 'ai-usage', label: t.adminSidebar.aiUsage, icon: '📊' },
    ]},
    { title: t.adminSidebar.groupAutomation, items: [
      { id: 'workflows', label: t.adminSidebar.workflows, icon: '⚙' },
      { id: 'automations', label: t.adminSidebar.automations, icon: '🔄' },
      { id: 'jobs', label: t.adminSidebar.jobs, icon: '⏱' },
    ]},
    { title: t.adminSidebar.groupSecurity, items: [
      { id: 'security-center', label: t.adminSidebar.securityCenter, icon: '🛡' },
      { id: 'sessions', label: t.adminSidebar.sessions, icon: '🔒' },
      { id: 'audit-logs', label: t.adminSidebar.auditLogs, icon: '📋' },
    ]},
    { title: t.adminSidebar.groupSystem, items: [
      { id: 'system-health', label: t.adminSidebar.systemHealth, icon: '🖥' },
      { id: 'monitoring', label: t.adminSidebar.monitoring, icon: '📈' },
      { id: 'backups', label: t.adminSidebar.backupRecovery, icon: '💾' },
      { id: 'notifications', label: t.adminSidebar.notificationsCenter, icon: '📢' },
      { id: 'system-settings', label: t.adminSidebar.systemSettings, icon: '⚙' },
    ]},
    { title: t.adminSidebar.groupSupport, items: [
      { id: 'tickets', label: t.adminSidebar.tickets, icon: '🎫' },
      { id: 'support', label: t.adminSidebar.supportPage, icon: '🎧' },
    ]},
  ];
  if (userRole === 'super_admin') {
    return [{ title: t.adminSidebar.groupMaster, items: [
      { id: 'overview', label: t.adminSidebar.overview, icon: '🏠' },
      { id: 'global-search', label: t.adminSidebar.globalSearch, icon: '🔍' },
    ]}, ...base];
  }
  return base;
}

interface AdminSidebarProps {
  currentPage: string;
  onNavigate: (page: string) => void;
  isRTL: boolean;
  isOpen: boolean;
  onToggle: () => void;
  userRole?: string;
}

export default function AdminSidebar({ currentPage, onNavigate, isRTL, isOpen, onToggle: _onToggle, userRole }: AdminSidebarProps) {
  const { t } = useI18n();
  const [collapsed, setCollapsed] = React.useState(false);
  const groups = getNavGroups(userRole || '', t);

  return (
    <aside
      className={`${isOpen ? 'flex' : 'hidden'} md:flex flex-col w-64 bg-white border-r border-gray-200 overflow-hidden shrink-0 fixed md:static inset-y-0 left-0 z-30 ${isRTL ? 'left-auto right-0' : ''} transition-all duration-300 ${collapsed ? 'w-16' : 'w-64'}`}
    >
      <div className="p-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">2TO</div>
          {!collapsed && <div><p className="font-bold text-gray-900 text-sm leading-tight">EOS</p><p className="text-xs text-gray-400">{t.adminSidebar.eosControlCenter}</p></div>}
        </div>
        <button onClick={() => setCollapsed(!collapsed)} className="p-1 rounded hover:bg-gray-100">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto p-2">
        {groups.map((group) => (
          <div key={group.title} className="mb-4">
            {!collapsed && <p className="px-2 text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">{group.title}</p>}
            {group.items.map((item) => (
              <button key={item.id} onClick={() => onNavigate(item.id)}
                className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm transition-colors ${currentPage === item.id ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'} ${isRTL ? 'flex-row-reverse' : ''}`}
                title={collapsed ? item.label : undefined}>
                <span className="text-base">{item.icon}</span>
                {!collapsed && <span>{item.label}</span>}
              </button>
            ))}
          </div>
        ))}
      </nav>
      <div className="p-3 border-t border-gray-100">
        <div className="flex items-center gap-2 px-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-purple-600 rounded-full flex items-center justify-center text-white text-xs font-bold">SA</div>
          {!collapsed && <div className="flex-1 min-w-0"><p className="text-sm font-medium text-gray-900 truncate">{t.adminSidebar.systemOwner}</p><p className="text-xs text-gray-400">{t.adminSidebar.superAdmin}</p></div>}
        </div>
      </div>
    </aside>
  );
}
