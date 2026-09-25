import React, { useState } from 'react';
import { useI18n } from '../i18n';
import AdminSidebar from './AdminSidebar';
import AdminHeader from './AdminHeader';

interface AdminLayoutProps {
  children: React.ReactNode;
  currentPage: string;
  onNavigate: (page: string) => void;
  token: string;
  userRole?: string;
}

export default function AdminLayout({ children, currentPage, onNavigate, token, userRole }: AdminLayoutProps) {
  const { isRTL } = useI18n();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className={`flex h-screen bg-gray-50 ${isRTL ? 'flex-row-reverse' : ''}`}>
      <AdminSidebar
        currentPage={currentPage}
        onNavigate={onNavigate}
        isRTL={isRTL}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        userRole={userRole}
      />
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/50 z-20 md:hidden" onClick={() => setSidebarOpen(false)} />
      )}
      <div className="flex-1 flex flex-col overflow-hidden">
        <AdminHeader token={token} onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
        <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
