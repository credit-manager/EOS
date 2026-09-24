import React, { useState } from 'react';
import { useI18n } from '../i18n';
import ConfirmDialog from './ConfirmDialog';
import LanguageSwitcher from './LanguageSwitcher';

interface AdminHeaderProps {
  token: string;
  onToggleSidebar: () => void;
}

export default function AdminHeader({ token: _token, onToggleSidebar }: AdminHeaderProps) {
  const { language, setLanguage, isRTL: _isRTL } = useI18n();
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [notifOpen, setNotifOpen] = useState(false);
  const [quickActionsOpen, setQuickActionsOpen] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [confirmAction, setConfirmAction] = useState('');

  const quickActions = [
    { id: 'new-tenant', label: 'New Tenant', icon: '🏢' },
    { id: 'new-user', label: 'New User', icon: '👤' },
    { id: 'new-plan', label: 'New Plan', icon: '💳' },
    { id: 'new-role', label: 'New Role', icon: '🔐' },
    { id: 'new-api-key', label: 'New API Key', icon: '🔑' },
    { id: 'new-ai-agent', label: 'New AI Agent', icon: '🤖' },
  ];

  const notifications = [
    { title: 'Critical: DB latency spike', time: '2m ago', type: 'critical' },
    { title: '3 new tenant signups', time: '15m ago', type: 'info' },
    { title: 'Payment gateway down', time: '1h ago', type: 'critical' },
    { title: 'AI model retrained', time: '3h ago', type: 'success' },
  ];

  const handleDangerous = (action: string) => {
    setConfirmAction(action);
    setShowConfirm(true);
  };

  return (
    <header className="bg-white border-b border-gray-200 px-4 md:px-6 py-3 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-3">
        <button className="md:hidden p-2" onClick={onToggleSidebar}>
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
        </button>
        <h1 className="text-lg font-bold text-gray-900 hidden sm:block">2TO EOS — Master Control Center</h1>
      </div>

      <div className="flex-1 max-w-xl mx-4 hidden md:block">
        <div className="relative">
          <input type="text" placeholder="Search tenants, users, invoices, API keys..."
            className="w-full px-4 py-2 pl-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            onFocus={() => setSearchOpen(true)}
            onBlur={() => setTimeout(() => setSearchOpen(false), 200)}
            value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
          <svg className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
          {searchOpen && searchQuery && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
              <div className="p-2 space-y-1">
                {[
                  { type: 'tenant', name: 'Acme Corp', id: 'T-001' },
                  { type: 'user', name: 'admin@acme.com', id: 'U-42' },
                  { type: 'invoice', name: 'INV-2026-001', id: 'I-001' },
                ].map((r, i) => (
                  <button key={i} className="w-full flex items-center gap-3 px-3 py-2 hover:bg-gray-50 rounded-lg text-sm">
                    <span>{r.type === 'tenant' ? '🏢' : r.type === 'user' ? '👤' : '📄'}</span>
                    <div className="text-left"><p className="font-medium text-gray-900">{r.name}</p><p className="text-xs text-gray-500">{r.id}</p></div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 md:gap-4">
        <LanguageSwitcher language={language} onSwitch={setLanguage} isRTL={_isRTL} />
        <button className="relative p-2 rounded-lg hover:bg-gray-100" onClick={() => setNotifOpen(!notifOpen)}>
          <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
        </button>
        {notifOpen && (
          <div className="absolute right-0 top-full mt-2 w-80 bg-white border border-gray-200 rounded-xl shadow-xl z-50 py-2">
            <p className="px-4 py-2 text-xs font-semibold text-gray-400 uppercase">Notifications</p>
            {notifications.map((n, i) => (
              <button key={i} className="w-full flex items-start gap-3 px-4 py-3 hover:bg-gray-50 text-left border-b border-gray-50">
                <span className={`w-2 h-2 mt-1.5 rounded-full shrink-0 ${n.type === 'critical' ? 'bg-red-500' : n.type === 'success' ? 'bg-green-500' : 'bg-blue-500'}`} />
                <div><p className="text-sm font-medium text-gray-900">{n.title}</p><p className="text-xs text-gray-500">{n.time}</p></div>
              </button>
            ))}
          </div>
        )}
        <div className="relative">
          <button className="flex items-center gap-2 p-1 rounded-lg hover:bg-gray-100" onClick={() => setQuickActionsOpen(!quickActionsOpen)}>
            <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-purple-600 rounded-full flex items-center justify-center text-white text-xs font-bold">SA</div>
          </button>
          {quickActionsOpen && (
            <div className="absolute right-0 top-full mt-2 w-64 bg-white border border-gray-200 rounded-xl shadow-xl z-50 py-2">
              <p className="px-4 py-2 text-xs font-semibold text-gray-400 uppercase">Quick Actions</p>
              {quickActions.map((a) => (
                <button key={a.id} className="w-full flex items-center gap-3 px-4 py-2 hover:bg-gray-50 text-sm text-left">
                  <span>{a.icon}</span><span>{a.label}</span>
                </button>
              ))}
              <div className="border-t border-gray-100 my-1" />
              <button className="w-full flex items-center gap-3 px-4 py-2 hover:bg-red-50 text-sm text-left text-red-600" onClick={() => handleDangerous('disable_system')}>
                <span>🚨</span><span>Disable System</span>
              </button>
            </div>
          )}
        </div>
      </div>
      <ConfirmDialog isOpen={showConfirm} onClose={() => setShowConfirm(false)} onConfirm={() => setShowConfirm(false)} title="Confirm Dangerous Action" message={`This will ${confirmAction}. This action cannot be undone. Please type "CONFIRM" to proceed.`} confirmText="Confirm" variant="danger" />
    </header>
  );
}
