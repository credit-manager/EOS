/**
 * EOS System — Branding Provider (P67)
 * Loads tenant white-label branding once at boot and applies it globally:
 * antd theme tokens, document direction, favicon, title, and locale.
 */

import React, { useEffect } from 'react';
import { ConfigProvider, Spin, theme as antdTheme } from 'antd';
import arEG from 'antd/locale/ar_EG';
import enUS from 'antd/locale/en_US';
import dayjs from 'dayjs';
import 'dayjs/locale/ar';
import { useBrandingStore } from '../stores/brandingStore';

/**
 * Resolve the tenant identity hint for branding lookup:
 * 1. Production domain (erp.company.com) → used directly
 * 2. Localhost → fall back to ?brand=slug or stored slug
 */
export function getTenantHint(): string | null {
  const host = window.location.hostname;
  const isLocal =
    host === 'localhost' ||
    host === '127.0.0.1' ||
    /^(\d{1,3}\.){3}\d{1,3}$/.test(host);
  if (!isLocal) return host;

  const params = new URLSearchParams(window.location.search);
  const q = params.get('brand');
  if (q) return q;
  return localStorage.getItem('tenant_slug') || null;
}

const BrandedShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const branding = useBrandingStore((s) => s.branding);
  const loaded = useBrandingStore((s) => s.loaded);
  const loadBranding = useBrandingStore((s) => s.loadBranding);

  // 1. Load branding on mount
  useEffect(() => {
    loadBranding(getTenantHint());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 2. Apply direction to the document (global RTL/LTR switch)
  //    Hooks before conditional return is safe
  useEffect(() => {
    if (branding) {
      document.documentElement.dir = branding.direction === 'ltr' ? 'ltr' : 'rtl';
    }
  }, [branding?.direction]);

  // 3. Keep dayjs locale in sync with branding direction
  useEffect(() => {
    dayjs.locale(branding?.direction === 'ltr' ? 'en' : 'ar');
  }, [branding?.direction]);

  // 4. Safe to early-return AFTER all hooks above
  if (!loaded || !branding) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f0f2f5' }}>
        <Spin size="large" />
      </div>
    );
  }

  const isDark = branding.theme_mode === 'dark';
  const isRTL = branding.direction !== 'ltr';

  const theme = {
    token: {
      colorPrimary: branding.primary_color || '#1890ff',
      colorInfo: branding.primary_color || '#1890ff',
      borderRadius: 8,
      fontFamily: "'Inter', 'Cairo', sans-serif",
    },
    algorithm: isDark ? antdTheme.darkAlgorithm : undefined,
    components: {
      Table: { headerBg: isDark ? '#1f1f1f' : '#fafafa' },
    },
  };

  return (
    <ConfigProvider locale={isRTL ? arEG : enUS} direction={isRTL ? 'rtl' : 'ltr'} theme={theme}>
      {children}
    </ConfigProvider>
  );
};

export default BrandedShell;
