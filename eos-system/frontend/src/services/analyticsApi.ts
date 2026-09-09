/**
 * EOS System — Analytics API Service (P65)
 * Advanced Analytics & Executive Dashboard
 */

import apiClient from './apiClient';
import type {
  ExecutiveSummary,
  KPI,
  RevenueTrendPoint,
  ExpensesTrendPoint,
  ProfitTrendPoint,
  CashFlowPoint,
  SalesSummary,
  SalesByPeriod,
  TopCustomer,
  PurchaseSummary,
  TopSupplier,
  InventorySummary,
  StockMovement,
  ProjectSummary,
  ProjectCostItem,
  HRSummary,
  BusinessAlert,
  RoleDashboard,
  DrillDownResult,
} from '../types';

export const analyticsApi = {
  // =====================================================
  // Executive Dashboard
  // =====================================================

  getExecutiveSummary: async (
    tenantId: string,
    period: string = 'this_month'
  ): Promise<ExecutiveSummary> => {
    return apiClient.get('/analytics/executive', {
      params: { tenant_id: tenantId, period },
    });
  },

  getKPIs: async (
    tenantId: string,
    period: string = 'this_month'
  ): Promise<{ kpis: KPI[] }> => {
    return apiClient.get('/analytics/kpis', {
      params: { tenant_id: tenantId, period },
    });
  },

  // =====================================================
  // Trends
  // =====================================================

  getRevenueTrend: async (
    tenantId: string,
    months: number = 12
  ): Promise<{ trend: RevenueTrendPoint[] }> => {
    return apiClient.get('/analytics/revenue-trend', {
      params: { tenant_id: tenantId, months },
    });
  },

  getExpensesTrend: async (
    tenantId: string,
    months: number = 12
  ): Promise<{ trend: ExpensesTrendPoint[] }> => {
    return apiClient.get('/analytics/expenses-trend', {
      params: { tenant_id: tenantId, months },
    });
  },

  getProfitTrend: async (
    tenantId: string,
    months: number = 12
  ): Promise<{ trend: ProfitTrendPoint[] }> => {
    return apiClient.get('/analytics/profit-trend', {
      params: { tenant_id: tenantId, months },
    });
  },

  getCashFlow: async (
    tenantId: string,
    months: number = 6
  ): Promise<{ cash_flow: CashFlowPoint[] }> => {
    return apiClient.get('/analytics/cash-flow', {
      params: { tenant_id: tenantId, months },
    });
  },

  // =====================================================
  // Sales Analytics
  // =====================================================

  getSalesSummary: async (
    tenantId: string,
    period: string = 'this_month'
  ): Promise<SalesSummary> => {
    return apiClient.get('/analytics/sales/summary', {
      params: { tenant_id: tenantId, period },
    });
  },

  getSalesPeriods: async (tenantId: string): Promise<SalesByPeriod> => {
    return apiClient.get('/analytics/sales/periods', {
      params: { tenant_id: tenantId },
    });
  },

  getTopCustomers: async (
    tenantId: string,
    limit: number = 10
  ): Promise<{ customers: TopCustomer[] }> => {
    return apiClient.get('/analytics/sales/top-customers', {
      params: { tenant_id: tenantId, limit },
    });
  },

  // =====================================================
  // Purchase Analytics
  // =====================================================

  getPurchaseSummary: async (
    tenantId: string,
    period: string = 'this_month'
  ): Promise<PurchaseSummary> => {
    return apiClient.get('/analytics/purchases/summary', {
      params: { tenant_id: tenantId, period },
    });
  },

  getTopSuppliers: async (
    tenantId: string,
    limit: number = 10
  ): Promise<{ suppliers: TopSupplier[] }> => {
    return apiClient.get('/analytics/purchases/top-suppliers', {
      params: { tenant_id: tenantId, limit },
    });
  },

  // =====================================================
  // Inventory Analytics
  // =====================================================

  getInventorySummary: async (tenantId: string): Promise<InventorySummary> => {
    return apiClient.get('/analytics/inventory', {
      params: { tenant_id: tenantId },
    });
  },

  getStockMovements: async (
    tenantId: string,
    days: number = 30
  ): Promise<{ movements: StockMovement[] }> => {
    return apiClient.get('/analytics/inventory/movements', {
      params: { tenant_id: tenantId, days },
    });
  },

  // =====================================================
  // Project Analytics
  // =====================================================

  getProjectSummary: async (tenantId: string): Promise<ProjectSummary> => {
    return apiClient.get('/analytics/projects', {
      params: { tenant_id: tenantId },
    });
  },

  getProjectCosts: async (
    tenantId: string
  ): Promise<{ projects: ProjectCostItem[] }> => {
    return apiClient.get('/analytics/projects/costs', {
      params: { tenant_id: tenantId },
    });
  },

  // =====================================================
  // HR Analytics
  // =====================================================

  getHRSummary: async (tenantId: string): Promise<HRSummary> => {
    return apiClient.get('/analytics/hr', {
      params: { tenant_id: tenantId },
    });
  },

  // =====================================================
  // Business Alerts
  // =====================================================

  getAlerts: async (tenantId: string): Promise<{ alerts: BusinessAlert[] }> => {
    return apiClient.get('/analytics/alerts', {
      params: { tenant_id: tenantId },
    });
  },

  // =====================================================
  // Role-Based Dashboard
  // =====================================================

  getRoleDashboard: async (
    tenantId: string,
    role: string,
    period: string = 'this_month'
  ): Promise<RoleDashboard> => {
    return apiClient.get(`/analytics/dashboard/${role}`, {
      params: { tenant_id: tenantId, period },
    });
  },

  // =====================================================
  // Drill-Down
  // =====================================================

  getDrillDown: async (
    tenantId: string,
    entityType: string,
    entityId: string
  ): Promise<DrillDownResult> => {
    return apiClient.get(`/analytics/drill-down/${entityType}/${entityId}`, {
      params: { tenant_id: tenantId },
    });
  },
};

export default analyticsApi;
