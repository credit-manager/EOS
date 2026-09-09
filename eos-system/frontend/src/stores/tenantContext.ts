/**
 * Tenant Context — stores current tenant info including industry.
 * Fetches sidebar menu from Industry Framework API.
 * Falls back to static INDUSTRY_MODULES if API unavailable.
 */

import { create } from 'zustand';
import { apiClient } from '../services/apiClient';

interface MenuItem {
  key: string;
  icon: string;
  label: string;
  labelAr: string;
  path: string;
  module: string;
}

interface TenantContext {
  tenantId: string | null;
  tenantName: string | null;
  industry: string | null;
  companyName: string | null;
  currency: string;
  modules: string[];
  menuItems: MenuItem[];
  setTenant: (data: {
    tenantId: string;
    tenantName?: string;
    industry?: string;
    companyName?: string;
    currency?: string;
    modules?: string[];
  }) => void;
  fetchMenu: () => Promise<void>;
  clearTenant: () => void;
  isImpersonating: () => boolean;
}

export const useTenantContext = create<TenantContext>((set, get) => ({
  tenantId: null,
  tenantName: null,
  industry: null,
  companyName: null,
  currency: 'SAR',
  modules: [],
  menuItems: [],

  setTenant: (data) => {
    set({
      tenantId: data.tenantId,
      tenantName: data.tenantName || null,
      industry: data.industry || null,
      companyName: data.companyName || null,
      currency: data.currency || 'SAR',
      modules: data.modules || [],
    });
    // Auto-fetch menu after setting tenant
    if (data.tenantId) {
      get().fetchMenu();
    }
  },

  fetchMenu: async () => {
    const { tenantId } = get();
    if (!tenantId) return;

    try {
      const res: any = await apiClient.get(`/framework/tenants/${tenantId}/menu`);
      if (res.data?.menu) {
        set({ menuItems: res.data.menu });
        return;
      }
    } catch {
      // API not available, fall through to static
    }

    // Fallback: use static INDUSTRY_MODULES
    const { industry } = get();
    if (industry && INDUSTRY_MODULES[industry]) {
      const items = INDUSTRY_MODULES[industry].map(m => ({
        ...m,
        module: m.key,
      }));
      set({ menuItems: items });
    }
  },

  clearTenant: () => set({
    tenantId: null,
    tenantName: null,
    industry: null,
    companyName: null,
    currency: 'SAR',
    modules: [],
    menuItems: [],
  }),

  isImpersonating: () => !!localStorage.getItem('eos_impersonate_token'),
}));

/**
 * Static industry module mapping — used as fallback when framework API unavailable.
 */
export const INDUSTRY_MODULES: Record<string, Array<{
  key: string;
  icon: string;
  label: string;
  labelAr: string;
  path: string;
}>> = {
  construction: [
    { key: 'dashboard', icon: 'HomeOutlined', label: 'Dashboard', labelAr: 'لوحة التحكم', path: '/construction' },
    { key: 'projects', icon: 'ProjectOutlined', label: 'Projects & Contracts', labelAr: 'المشاريع والعقود', path: '/construction?tab=projects' },
    { key: 'stock', icon: 'ShopOutlined', label: 'Materials & Stock', labelAr: 'المخزون والمواد', path: '/construction?tab=stock' },
    { key: 'procurement', icon: 'ShoppingCartOutlined', label: 'Procurement', labelAr: 'المشتريات', path: '/construction?tab=procurement' },
    { key: 'suppliers', icon: 'TeamOutlined', label: 'Suppliers', labelAr: 'الموردون', path: '/construction?tab=suppliers' },
    { key: 'clients', icon: 'UserOutlined', label: 'Clients', labelAr: 'العملاء', path: '/construction?tab=clients' },
  ],
  trading: [
    { key: 'dashboard', icon: 'HomeOutlined', label: 'Dashboard', labelAr: 'لوحة التحكم', path: '/trading' },
    { key: 'sales', icon: 'ShoppingCartOutlined', label: 'Sales', labelAr: 'المبيعات', path: '/trading' },
    { key: 'purchases', icon: 'ImportOutlined', label: 'Purchasing', labelAr: 'المشتريات', path: '/trading' },
    { key: 'inventory', icon: 'ShopOutlined', label: 'Inventory', labelAr: 'المخزون', path: '/trading' },
    { key: 'customers', icon: 'UserOutlined', label: 'Customers', labelAr: 'العملاء', path: '/trading' },
    { key: 'suppliers', icon: 'TeamOutlined', label: 'Suppliers', labelAr: 'الموردون', path: '/trading' },
    { key: 'pricing', icon: 'AccountBookOutlined', label: 'Pricing', labelAr: 'التسعير', path: '/trading' },
  ],
  retail: [
    { key: 'dashboard', icon: 'DashboardOutlined', label: 'Dashboard', labelAr: 'لوحة التحكم', path: '/retail' },
    { key: 'pos', icon: 'ShoppingCartOutlined', label: 'Point of Sale', labelAr: 'نقطة البيع', path: '/retail' },
    { key: 'cash', icon: 'WalletOutlined', label: 'Cash Management', labelAr: 'إدارة النقد', path: '/retail' },
    { key: 'loyalty', icon: 'TrophyOutlined', label: 'Loyalty', labelAr: 'الولاء', path: '/retail' },
    { key: 'promotions', icon: 'PercentageOutlined', label: 'Promotions', labelAr: 'العروض', path: '/retail' },
    { key: 'analytics', icon: 'BarChartOutlined', label: 'Analytics', labelAr: 'التحليلات', path: '/retail' },
  ],
  restaurant: [
    { key: 'dashboard', icon: 'DashboardOutlined', label: 'Dashboard', labelAr: 'لوحة التحكم', path: '/restaurant' },
    { key: 'floor', icon: 'AppstoreOutlined', label: 'Floor & Tables', labelAr: 'المخطط والطاولات', path: '/restaurant' },
    { key: 'pos', icon: 'ShoppingCartOutlined', label: 'POS & Orders', labelAr: 'نقطة البيع والطلبات', path: '/restaurant' },
    { key: 'kitchen', icon: 'FireOutlined', label: 'Kitchen KDS', labelAr: 'المطبخ', path: '/restaurant' },
    { key: 'menu', icon: 'MenuOutlined', label: 'Menu & Recipes', labelAr: 'القائمة والوصفات', path: '/restaurant' },
    { key: 'inventory', icon: 'ShopOutlined', label: 'Inventory & Waste', labelAr: 'المخزون والهدر', path: '/restaurant' },
    { key: 'cash', icon: 'DollarOutlined', label: 'Cash Drawer', labelAr: 'الخزينة', path: '/restaurant' },
    { key: 'analytics', icon: 'BarChartOutlined', label: 'Analytics', labelAr: 'التحليلات', path: '/restaurant' },
  ],
  services: [
    { key: 'dashboard', icon: 'HomeOutlined', label: 'Dashboard', labelAr: 'لوحة التحكم', path: '/dashboard' },
    { key: 'projects', icon: 'ProjectOutlined', label: 'Projects', labelAr: 'المشاريع', path: '/projects' },
    { key: 'clients', icon: 'UserOutlined', label: 'Clients', labelAr: 'العملاء', path: '/sales?tab=customers' },
    { key: 'invoicing', icon: 'FileTextOutlined', label: 'Invoicing', labelAr: 'الفواتير', path: '/sales' },
    { key: 'accounting', icon: 'AccountBookOutlined', label: 'Accounting', labelAr: 'المحاسبة', path: '/accounting' },
    { key: 'hr', icon: 'TeamOutlined', label: 'HR', labelAr: 'الموارد البشرية', path: '/hr' },
    { key: 'reports', icon: 'BarChartOutlined', label: 'Reports', labelAr: 'التقارير', path: '/analytics' },
  ],
  manufacturing: [
    { key: 'dashboard', icon: 'HomeOutlined', label: 'Dashboard', labelAr: 'لوحة التحكم', path: '/dashboard' },
    { key: 'mfg', icon: 'ToolOutlined', label: 'Manufacturing', labelAr: 'التصنيع', path: '/manufacturing' },
    { key: 'production', icon: 'SettingOutlined', label: 'Production', labelAr: 'الإنتاج', path: '/projects' },
    { key: 'inventory', icon: 'ShopOutlined', label: 'Materials & Stock', labelAr: 'المخزون والمواد', path: '/inventory' },
    { key: 'procurement', icon: 'ShoppingCartOutlined', label: 'Procurement', labelAr: 'المشتريات', path: '/inventory?tab=procurement' },
    { key: 'customers', icon: 'UserOutlined', label: 'Customers', labelAr: 'العملاء', path: '/sales?tab=customers' },
    { key: 'accounting', icon: 'AccountBookOutlined', label: 'Accounting', labelAr: 'المحاسبة', path: '/accounting' },
    { key: 'hr', icon: 'TeamOutlined', label: 'HR', labelAr: 'الموارد البشرية', path: '/hr' },
    { key: 'quality', icon: 'CheckCircleOutlined', label: 'Quality Control', labelAr: 'مراقبة الجودة', path: '/projects?tab=quality' },
    { key: 'reports', icon: 'BarChartOutlined', label: 'Reports', labelAr: 'التقارير', path: '/analytics' },
  ],
};
