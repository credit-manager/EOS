import React from 'react';
import { TranslationKeys } from '../i18n';

interface SidebarProps {
  t: TranslationKeys;
  currentPage: string;
  onNavigate: (page: string) => void;
  isRTL: boolean;
}

const navItems = [
  { key: 'dashboard', icon: '📊' },
  { key: 'projects', icon: '🏗️' },
  { key: 'contracts', icon: '📋' },
  { key: 'boq', icon: '📑' },
  { key: 'claims', icon: '📝' },
  { key: 'procurements', icon: '🛒' },
  { key: 'financial', icon: '💰' },
  { key: 'reports', icon: '📈' },
  { key: 'users', icon: '👥' },
  { key: 'audit', icon: '🔍' },
  { key: 'settings', icon: '⚙️' },
];

export default function Sidebar({ t, currentPage, onNavigate, isRTL }: SidebarProps) {
  const nav = t.nav as Record<string, string>;

  return (
    <aside
      className={`w-64 bg-white border-r border-gray-200 flex flex-col ${
        isRTL ? 'border-r-0 border-l' : ''
      }`}
    >
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-xl font-bold text-gray-900">{t.app.name}</h1>
        <p className="text-sm text-gray-500 mt-1">{t.app.description}</p>
      </div>

      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <button
            key={item.key}
            onClick={() => onNavigate(item.key)}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              currentPage === item.key
                ? 'bg-blue-50 text-blue-700'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            } ${isRTL ? 'flex-row-reverse' : ''}`}
          >
            <span className="text-lg">{item.icon}</span>
            <span>{nav[item.key]}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
