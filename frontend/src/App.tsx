import { useState, useEffect } from 'react';
import { useI18n } from './i18n';
import { api } from './api';
import LanguageSwitcher from './components/LanguageSwitcher';
import { ExecutiveDashboard } from './pages/ExecutiveDashboard';
import { BusinessObjectsExplorer } from './pages/BusinessObjectsExplorer';
import { EntityPage } from './pages/EntityPage';
import { BusinessGraphPage } from './pages/BusinessGraphPage';
import { WorkflowsPage } from './pages/WorkflowsPage';
import { RulesPage } from './pages/RulesPage';
import { EventsPage } from './pages/EventsPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { AICopilotPage } from './pages/AICopilotPage';
import DocumentsPage from './components/DocumentsPage';
import IntegrationsPage from './components/IntegrationsPage';
import GlobalizationPage from './components/GlobalizationPage';
import BuilderPage from './components/BuilderPage';
import SDKPage from './components/SDKPage';
import MarketplacePage from './components/MarketplacePage';
import ProjectsPage from './components/ProjectsPage';
import ContractsPage from './components/ContractsPage';
import BOQPage from './components/BOQPage';
import ClaimsPage from './components/ClaimsPage';
import ProcurementsPage from './components/ProcurementsPage';
import FinancialPage from './components/FinancialPage';
import ReportsPage from './components/ReportsPage';
import UsersPage from './components/UsersPage';
import NotificationsPage from './components/NotificationsPage';
import AuditPage from './components/AuditPage';
import SettingsPage from './components/SettingsPage';

import OnboardingWizard from './components/OnboardingWizard';
import LandingPage from './components/LandingPage';
import AdminLayout from './components/AdminLayout';
import MasterDashboard from './pages/MasterDashboard';
import TenantManagement from './pages/TenantManagement';
import UserManagement from './pages/UserManagement';
import RolesPermissions from './pages/RolesPermissions';
import SubscriptionPlans from './pages/SubscriptionPlans';
import BillingCenter from './pages/BillingCenter';
import FeatureFlags from './pages/FeatureFlags';
import AIControlCenter from './pages/AIControlCenter';
import AutomationCenter from './pages/AutomationCenter';
import IntegrationsHub from './pages/IntegrationsHub';
import APIManagement from './pages/APIManagement';
import SecurityCenter from './pages/SecurityCenter';
import AuditLogsPage from './pages/AuditLogsPage';
import SystemSettingsPage from './pages/SystemSettingsPage';
import SystemHealthPage from './pages/SystemHealthPage';
import BackupRecoveryPage from './pages/BackupRecoveryPage';
import NotificationsCenterPage from './pages/NotificationsCenterPage';
import SupportCenterPage from './pages/SupportCenterPage';
import GlobalSearchPage from './pages/GlobalSearchPage';
import ApplicationsPage from './pages/ApplicationsPage';
import WorkflowsAdminPage from './pages/WorkflowsAdminPage';

interface User {
  user_id: string;
  email: string;
  tenant_id: string;
  role: string;
}

type Page =
  | 'home'
  | 'objects'
  | 'entity'
  | 'graph'
  | 'workflows'
  | 'rules'
  | 'events'
  | 'analytics'
  | 'ai'
  | 'documents'
  | 'integrations'
  | 'globalization'
  | 'builder'
  | 'sdk'
  | 'marketplace'
  | 'projects'
  | 'contracts'
  | 'boq'
  | 'claims'
  | 'procurements'
  | 'financial'
  | 'reports'
  | 'users'
  | 'notifications'
  | 'audit'
  | 'settings'
  | 'workspace'
  | 'master'
  | 'overview'
  | 'tenants'
  | 'users-admin'
  | 'roles'
  | 'plans'
  | 'billing'
  | 'feature-flags'
  | 'ai-control'
  | 'ai-models'
  | 'ai-workforce'
  | 'ai-usage'
  | 'automation'
  | 'jobs'
  | 'applications'
  | 'api'
  | 'security-center'
  | 'sessions'
  | 'audit-logs'
  | 'system-health'
  | 'monitoring'
  | 'backups'
  | 'system-settings'
  | 'tickets'
  | 'global-search'
  | 'integrations-hub'
  | 'notifications-center'
  | 'workflows-admin'
  | 'automations';

interface NavItem {
  id: Page;
  label: string;
  icon: string;
}

const platformNav: NavItem[] = [
  { id: 'home', label: 'Home', icon: '🏠' },
  { id: 'objects', label: 'Business Objects', icon: '📦' },
  { id: 'graph', label: 'Business Graph', icon: '🕸' },
  { id: 'workflows', label: 'Workflows', icon: '⚡' },
  { id: 'rules', label: 'Rules', icon: '📜' },
  { id: 'events', label: 'Events', icon: '🔔' },
  { id: 'analytics', label: 'Analytics', icon: '📊' },
  { id: 'ai', label: 'AI Copilot', icon: '🤖' },
  { id: 'documents', label: 'Documents', icon: '📄' },
  { id: 'integrations-hub', label: 'Integrations', icon: '🔗' },
  { id: 'globalization', label: 'Globalization', icon: '🌍' },
  { id: 'builder', label: 'Builder', icon: '🔨' },
  { id: 'sdk', label: 'Developer SDK', icon: '🧑‍💻' },
  { id: 'marketplace', label: 'Marketplace', icon: '🏪' },
  { id: 'workspace', label: 'Workspace', icon: '🏢' },
];

const erpNav: NavItem[] = [
  { id: 'projects', label: 'Projects', icon: '🏗' },
  { id: 'contracts', label: 'Contracts', icon: '📋' },
  { id: 'boq', label: 'BOQ', icon: '📑' },
  { id: 'claims', label: 'Claims', icon: '📑' },
  { id: 'procurements', label: 'Procurement', icon: '🛒' },
  { id: 'financial', label: 'Financial', icon: '💰' },
  { id: 'reports', label: 'Reports', icon: '📈' },
];

const adminNav: NavItem[] = [
  { id: 'users', label: 'Users', icon: '👥' },
  { id: 'notifications', label: 'Notifications', icon: '🔔' },
  { id: 'audit', label: 'Audit', icon: '🔍' },
  { id: 'settings', label: 'Settings', icon: '⚙' },
];

const masterNav: NavItem[] = [
  { id: 'overview', label: 'Overview', icon: '🏠' },
  { id: 'tenants', label: 'Tenants', icon: '🏢' },
  { id: 'users-admin', label: 'Users', icon: '👥' },
  { id: 'roles', label: 'Roles & Permissions', icon: '🔐' },
  { id: 'plans', label: 'Plans', icon: '💳' },
  { id: 'billing', label: 'Billing', icon: '💰' },
  { id: 'feature-flags', label: 'Feature Flags', icon: '⚡' },
  { id: 'ai-control', label: 'AI Control Center', icon: '🤖' },
  { id: 'automation', label: 'Automation', icon: '⚙' },
  { id: 'integrations-hub', label: 'Integrations', icon: '🔗' },
  { id: 'applications', label: 'Applications', icon: '📱' },
  { id: 'api', label: 'API Management', icon: '🔑' },
  { id: 'security-center', label: 'Security Center', icon: '🛡' },
  { id: 'audit-logs', label: 'Audit Logs', icon: '📋' },
  { id: 'system-health', label: 'System Health', icon: '🖥' },
  { id: 'backups', label: 'Backup & Recovery', icon: '💾' },
  { id: 'notifications-center', label: 'Notifications', icon: '📢' },
  { id: 'tickets', label: 'Support', icon: '🎫' },
  { id: 'global-search', label: 'Search', icon: '🔍' },
];

export default function App() {
  const { language, setLanguage, t, isRTL } = useI18n();
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<Page>('home');
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [hydrating, setHydrating] = useState(true);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const [showLogin, setShowLogin] = useState(false);

  useEffect(() => {
    document.documentElement.dir = isRTL ? 'rtl' : 'ltr';
    document.documentElement.lang = language;
  }, [language, isRTL]);

  useEffect(() => {
    const storedToken = localStorage.getItem('2to_eos_access_token');
    if (storedToken) {
      setToken(storedToken);
      fetch('/api/v1/auth/me', { headers: { Authorization: `Bearer ${storedToken}` } })
        .then((r) => {
          if (!r.ok) throw new Error('not authenticated');
          return r.json();
        })
        .then((me) => {
          setUser({ user_id: me.user_id, email: me.email, tenant_id: me.tenant_id, role: me.role });
          setHydrating(false);
          api<{ company_name?: string }>('/settings', storedToken)
            .then((s) => { if (!s.company_name) setNeedsOnboarding(true); })
            .catch(() => {});
        })
        .catch(() => {
          localStorage.removeItem('2to_eos_access_token');
          localStorage.removeItem('2to_eos_refresh_token');
          setToken(null);
          setHydrating(false);
        });
    } else {
      setHydrating(false);
    }
  }, []);

  const handleLogin = async (email: string, password: string) => {
    try {
      const response = await fetch('/api/v1/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) return;
      const data = await response.json();
      const meR = await fetch('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });
      const me = meR.ok ? await meR.json() : null;
      localStorage.setItem('2to_eos_access_token', data.access_token);
      if (data.refresh_token) localStorage.setItem('2to_eos_refresh_token', data.refresh_token);
      setToken(data.access_token);
      setUser(me ?? { user_id: data.user_id, email, tenant_id: data.tenant_id, role: data.role });
      setCurrentPage('home');
      api<{ company_name?: string }>('/settings', data.access_token)
        .then((s) => { if (!s.company_name) setNeedsOnboarding(true); })
        .catch(() => {});
    } catch {
      // login failed silently
    }
  };

  const handleLogout = () => {
    if (token) {
      fetch('/api/v1/auth/logout', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => {});
    }
    localStorage.removeItem('2to_eos_access_token');
    localStorage.removeItem('2to_eos_refresh_token');
    setToken(null);
    setUser(null);
    setCurrentPage('home');
    setSelectedEntity(null);
    setShowLogin(false);
  };

  const navigate = (page: Page) => {
    setCurrentPage(page);
    if (page !== 'entity') setSelectedEntity(null);
  };

  if (hydrating) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-500 text-lg">{t.common.loading}</p>
      </div>
    );
  }

  if (!token || !user) {
    if (showLogin) {
      return <LoginScreen onLogin={handleLogin} onBack={() => setShowLogin(false)} />;
    }
    return <LandingPage onShowLogin={() => setShowLogin(true)} />;
  }

  if (needsOnboarding) {
    return (
      <OnboardingWizard
        onComplete={() => setNeedsOnboarding(false)}
      />
    );
  }

  return (
    <div className={`flex h-screen bg-gray-50 ${isRTL ? 'flex-row-reverse' : ''}`}>
      <Sidebar
        currentPage={currentPage}
        onNavigate={(page) => {
          navigate(page);
          setSidebarOpen(false);
        }}
        onLogout={handleLogout}
        user={user}
        isRTL={isRTL}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white border-b border-gray-200 px-4 md:px-6 py-3 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <button
              className="md:hidden p-2"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h1 className="text-lg font-bold text-gray-900">{t.app.name}</h1>
          </div>
          <div className="flex items-center gap-2 md:gap-4">
            <LanguageSwitcher language={language} onSwitch={setLanguage} isRTL={isRTL} />
            <span className="hidden md:inline text-sm text-gray-600">{user.email}</span>
            <span className="hidden sm:inline text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium">
              {user.role}
            </span>
            <button onClick={handleLogout} className="text-sm text-red-600 hover:text-red-800">
              <span className="hidden md:inline">{t.auth.logout}</span>
              <span className="md:hidden">{t.auth.logout}</span>
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-4 md:p-6">{renderPage()}</main>
      </div>
    </div>
  );

  function renderPage() {
    const tokenStr = token!;
    const role = user!.role;
    switch (currentPage) {
      case 'home':
        return <ExecutiveDashboard token={tokenStr} />;
      case 'objects':
        return (
          <BusinessObjectsExplorer
            token={tokenStr}
            role={role}
            onSelect={(code) => {
              setSelectedEntity(code);
              setCurrentPage('entity');
            }}
          />
        );
      case 'entity':
        return selectedEntity ? (
          <EntityPage
            token={tokenStr}
            role={role}
            entityCode={selectedEntity}
            onBack={() => setCurrentPage('objects')}
          />
        ) : (
          <BusinessObjectsExplorer
            token={tokenStr}
            role={role}
            onSelect={(code) => {
              setSelectedEntity(code);
              setCurrentPage('entity');
            }}
          />
        );
      case 'graph':
        return <BusinessGraphPage token={tokenStr} />;
      case 'workflows':
        return <WorkflowsPage token={tokenStr} role={role} />;
      case 'rules':
        return <RulesPage token={tokenStr} role={role} />;
      case 'events':
        return <EventsPage token={tokenStr} />;
      case 'analytics':
        return <AnalyticsPage token={tokenStr} />;
      case 'ai':
        return <AICopilotPage token={tokenStr} />;
      case 'documents':
        return <DocumentsPage token={tokenStr} />;
      case 'integrations':
        return <IntegrationsPage token={tokenStr} />;
      case 'globalization':
        return <GlobalizationPage token={tokenStr} />;
      case 'builder':
        return <BuilderPage token={tokenStr} />;
      case 'sdk':
        return <SDKPage token={tokenStr} />;
      case 'marketplace':
        return <MarketplacePage token={tokenStr} />;
      case 'projects':
        return <ProjectsPage t={t} token={tokenStr} />;
      case 'contracts':
        return <ContractsPage token={tokenStr} />;
      case 'boq':
        return <BOQPage token={tokenStr} />;
      case 'claims':
        return <ClaimsPage t={t} token={tokenStr} />;
      case 'procurements':
        return <ProcurementsPage t={t} token={tokenStr} />;
      case 'financial':
        return <FinancialPage t={t} token={tokenStr} />;
      case 'reports':
        return <ReportsPage t={t} token={tokenStr} />;
      case 'users':
        return <UsersPage t={t} token={tokenStr} />;
      case 'notifications':
        return <NotificationsPage token={tokenStr} />;
      case 'audit':
        return <AuditPage token={tokenStr} />;
      case 'settings':
        return <SettingsPage token={tokenStr} />;
      case 'master': {
        if (!user || user.role !== 'super_admin') {
          return <ExecutiveDashboard token={tokenStr} />;
        }
        const page = currentPage as string;
        const renderMasterPage = () => {
          switch (page) {
            case 'overview': return <MasterDashboard />;
            case 'tenants': return <TenantManagement />;
            case 'users-admin': return <UserManagement />;
            case 'roles': return <RolesPermissions />;
            case 'plans': return <SubscriptionPlans />;
            case 'billing': return <BillingCenter />;
            case 'feature-flags': return <FeatureFlags />;
            case 'ai-control': case 'ai-models': case 'ai-workforce': case 'ai-usage': return <AIControlCenter />;
            case 'workflows-admin': return <WorkflowsAdminPage />;
            case 'automations': case 'jobs': return <AutomationCenter />;
            case 'integrations-hub': return <IntegrationsHub />;
            case 'applications': return <ApplicationsPage />;
            case 'api': return <APIManagement />;
            case 'security-center': case 'sessions': return <SecurityCenter />;
            case 'audit-logs': return <AuditLogsPage />;
            case 'system-health': case 'monitoring': return <SystemHealthPage />;
            case 'backups': return <BackupRecoveryPage />;
            case 'notifications-center': return <NotificationsCenterPage />;
            case 'system-settings': return <SystemSettingsPage />;
            case 'tickets': return <SupportCenterPage />;
            case 'global-search': return <GlobalSearchPage />;
            default: return <MasterDashboard />;
          }
        };
        return <AdminLayout token={tokenStr} currentPage={currentPage} onNavigate={(p: string) => setCurrentPage(p as Page)} userRole={user?.role}>{renderMasterPage()}</AdminLayout>;
      }
      default:
        return <ExecutiveDashboard token={tokenStr} />;
    }
  }
}

function Sidebar({
  currentPage,
  onNavigate,
  user,
  isRTL,
  isOpen,
}: {
  currentPage: Page;
  onNavigate: (p: Page) => void;
  onLogout: () => void;
  user: User;
  isRTL: boolean;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const { t } = useI18n();
  const renderNavGroup = (title: string, items: NavItem[], labelFor: (id: Page) => string) => (
    <div className="mb-4">
      <p className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">
        {title}
      </p>
      {items.map((item) => (
        <button
          key={item.id}
          onClick={() => onNavigate(item.id)}
          className={`w-full text-left px-3 py-2 rounded-lg text-sm flex items-center gap-2 transition-colors ${
            currentPage === item.id
              ? 'bg-blue-50 text-blue-700 font-medium'
              : 'text-gray-600 hover:bg-gray-100'
          } ${isRTL ? 'flex-row-reverse' : ''}`}
        >
          <span className="text-base">{item.icon}</span>
          <span>{labelFor(item.id)}</span>
        </button>
      ))}
    </div>
  );

  const navLabel = (id: Page): string => {
    switch (id) {
      case 'home': return t.nav.home;
      case 'objects': return t.nav.businessObjects;
      case 'graph': return t.nav.businessGraph;
      case 'workflows': return t.nav.workflows;
      case 'rules': return t.nav.rules;
      case 'events': return t.nav.events;
      case 'analytics': return t.nav.analytics;
      case 'ai': return t.nav.aiCopilot;
      case 'documents': return t.nav.documents;
      case 'integrations-hub': return t.nav.integrations;
      case 'globalization': return t.nav.globalization;
      case 'builder': return t.nav.builder;
      case 'sdk': return t.nav.developerSdk;
      case 'marketplace': return t.nav.marketplace;
      case 'workspace': return t.nav.workspace;
      case 'projects': return t.nav.projects;
      case 'contracts': return t.nav.contracts;
      case 'boq': return t.nav.boq;
      case 'claims': return t.nav.claims;
      case 'procurements': return t.nav.procurements;
      case 'financial': return t.nav.financial;
      case 'reports': return t.nav.reports;
      case 'users': return t.nav.users;
      case 'notifications': return t.nav.notifications;
      case 'audit': return t.nav.audit;
      case 'settings': return t.nav.settings;
      case 'overview': return t.nav.overview;
      case 'tenants': return t.nav.tenants;
      case 'users-admin': return t.nav.users;
      case 'roles': return t.nav.rolesPermissions;
      case 'plans': return t.nav.plans;
      case 'billing': return t.nav.billing;
      case 'feature-flags': return t.nav.featureFlags;
      case 'ai-control':
      case 'ai-models':
      case 'ai-workforce':
      case 'ai-usage': return t.nav.aiControlCenter;
      case 'automation':
      case 'jobs': return t.nav.automation;
      case 'applications': return t.nav.applications;
      case 'api': return t.nav.apiManagement;
      case 'security-center':
      case 'sessions': return t.nav.securityCenter;
      case 'audit-logs': return t.nav.auditLogs;
      case 'system-health':
      case 'monitoring': return t.nav.systemHealth;
      case 'backups': return t.nav.backupRecovery;
      case 'notifications-center': return t.nav.notifications;
      case 'tickets': return t.nav.support;
      case 'global-search': return t.nav.search;
      default: return id;
    }
  };

  return (
    <aside
      className={`${isOpen ? 'flex' : 'hidden'} md:flex flex-col w-64 bg-white border-r border-gray-200 overflow-hidden shrink-0 fixed md:static inset-y-0 left-0 z-30 ${isRTL ? 'left-auto right-0' : ''}`}
    >
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
            E
          </div>
          <div>
            <p className="font-bold text-gray-900 text-sm leading-tight">{t.app.name}</p>
            <p className="text-xs text-gray-400">{t.app.description}</p>
          </div>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto p-3">
        {renderNavGroup(t.sidebar.platform, platformNav, navLabel)}
        {renderNavGroup(t.sidebar.erp, erpNav, navLabel)}
        {renderNavGroup(t.sidebar.administration, adminNav, navLabel)}
        {renderNavGroup(t.sidebar.master, masterNav, navLabel)}
      </nav>
      <div className="p-3 border-t border-gray-100">
        <div className="flex items-center gap-2 px-3 py-2">
          <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center text-xs font-medium text-gray-600">
            {user.email[0].toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">{user.email}</p>
            <p className="text-xs text-gray-400">{user.role}</p>
          </div>
        </div>
      </div>
    </aside>
  );
}

function LoginScreen({ onLogin, onBack }: { onLogin: (email: string, password: string) => void; onBack: () => void }) {
  const { language, setLanguage, isRTL, t } = useI18n();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    await onLogin(email, password);
    setLoading(false);
  };

  return (
    <div className={`min-h-screen flex items-center justify-center bg-gray-50 ${isRTL ? 'rtl' : 'ltr'}`}>
      <div className="w-full max-w-md p-8 bg-white rounded-xl shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <button onClick={onBack} className="text-sm text-gray-500 hover:text-gray-700">
            ← {t.login.backToHome}
          </button>
          <LanguageSwitcher language={language} onSwitch={setLanguage} isRTL={isRTL} />
        </div>
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white font-bold text-lg">
            E
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">{t.login.title}</h1>
            <p className="text-sm text-gray-500">{t.login.subtitle}</p>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t.login.emailLabel}</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t.login.passwordLabel}</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {loading ? t.login.signingIn : t.login.signIn}
          </button>
        </form>
      </div>
    </div>
  );
}
