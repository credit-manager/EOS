import React, { useState, useEffect } from 'react';
import { useI18n } from './i18n';
import Dashboard from './components/Dashboard';
import ProjectsPage from './components/ProjectsPage';
import ContractsPage from './components/ContractsPage';
import ClaimsPage from './components/ClaimsPage';
import ProcurementsPage from './components/ProcurementsPage';
import BOQPage from './components/BOQPage';
import FinancialPage from './components/FinancialPage';
import ReportsPage from './components/ReportsPage';
import UsersPage from './components/UsersPage';
import NotificationsPage from './components/NotificationsPage';
import AuditPage from './components/AuditPage';
import SettingsPage from './components/SettingsPage';
import Sidebar from './components/Sidebar';
import LanguageSwitcher from './components/LanguageSwitcher';

interface User {
  id: string;
  email: string;
  tenant_id: string;
  role: string;
}

export default function App() {
  const { language, setLanguage, t, isRTL } = useI18n();
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    document.documentElement.dir = isRTL ? 'rtl' : 'ltr';
    document.documentElement.lang = language;
  }, [language, isRTL]);

  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
      setIsAuthenticated(true);
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
      const meResponse = await fetch('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });
      const me = meResponse.ok ? await meResponse.json() : null;
      const currentUser: User = {
        id: data.user_id,
        email: me?.email ?? email,
        tenant_id: data.tenant_id,
        role: data.role,
      };
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user', JSON.stringify(currentUser));
      setToken(data.access_token);
      setUser(currentUser);
      setIsAuthenticated(true);
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard t={t} token={token!} />;
      case 'projects':
        return <ProjectsPage t={t} token={token!} />;
      case 'contracts':
        return <ContractsPage t={t} token={token!} />;
      case 'claims':
        return <ClaimsPage t={t} token={token!} />;
      case 'procurements':
        return <ProcurementsPage t={t} token={token!} />;
      case 'boq':
        return <BOQPage t={t} token={token!} />;
      case 'financial':
        return <FinancialPage t={t} token={token!} />;
      case 'reports':
        return <ReportsPage t={t} token={token!} />;
      case 'users':
        return <UsersPage t={t} token={token!} />;
      case 'notifications':
        return <NotificationsPage t={t} token={token!} />;
      case 'audit':
        return <AuditPage t={t} token={token!} />;
      case 'settings':
        return <SettingsPage t={t} token={token!} />;
      default:
        return (
          <div className="flex items-center justify-center h-64">
            <p className="text-gray-500">{t.common.noData}</p>
          </div>
        );
    }
  };

  if (!isAuthenticated) {
    return <LoginScreen t={t} onLogin={handleLogin} />;
  }

  return (
    <div className={`flex h-screen bg-gray-50 ${isRTL ? 'flex-row-reverse' : ''}`}>
      <Sidebar t={t} currentPage={currentPage} onNavigate={setCurrentPage} isRTL={isRTL} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            {(t.nav as Record<string, string>)[currentPage] || currentPage}
          </h2>
          <div className="flex items-center gap-4">
            <LanguageSwitcher language={language} onSwitch={setLanguage} isRTL={isRTL} />
            <span className="text-sm text-gray-600">{user?.email}</span>
            <button onClick={handleLogout} className="text-sm text-red-600 hover:text-red-800">
              {t.auth.logout}
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">{renderPage()}</main>
      </div>
    </div>
  );
}

function LoginScreen({
  t,
  onLogin,
}: {
  t: {
    app: { name: string; description: string };
    auth: { email: string; password: string; login: string };
  };
  onLogin: (email: string, password: string) => void;
}) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onLogin(email, password);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-xl shadow-lg">
        <h1 className="text-2xl font-bold text-center text-gray-900 mb-2">{t.app.name}</h1>
        <p className="text-center text-gray-500 mb-8">{t.app.description}</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t.auth.email}</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t.auth.password}
            </label>
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
            className="w-full py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            {t.auth.login}
          </button>
        </form>
      </div>
    </div>
  );
}
