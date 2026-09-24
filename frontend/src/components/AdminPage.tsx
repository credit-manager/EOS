import React from 'react';
import { useI18n } from '../i18n';

interface AdminPageProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

export default function AdminPage({ title, subtitle, children }: AdminPageProps) {
  const { isRTL } = useI18n();
  return (
    <div className={`space-y-6 ${isRTL ? 'direction=rtl' : ''}`}>
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
        {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}
