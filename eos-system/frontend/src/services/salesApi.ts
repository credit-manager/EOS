/**
 * EOS System — Sales & CRM API Service
 */

import apiClient from './apiClient';
import type {
  Customer,
  CustomerCreate,
  Lead,
  LeadCreate,
  Opportunity,
  OpportunityCreate,
  Quote,
  QuoteCreate,
  PaginatedResponse,
} from '../types';

export const salesApi = {
  // =====================================================
  // Customers
  // =====================================================

  // List customers
  listCustomers: async (params?: {
    type?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Customer>> => {
    return apiClient.get('/sales/customers', { params });
  },

  // Get customer by ID
  getCustomer: async (id: string): Promise<Customer> => {
    return apiClient.get(`/sales/customers/${id}`);
  },

  // Create customer
  createCustomer: async (data: CustomerCreate): Promise<Customer> => {
    return apiClient.post('/sales/customers', data);
  },

  // Update customer
  updateCustomer: async (id: string, data: Partial<CustomerCreate>): Promise<Customer> => {
    return apiClient.put(`/sales/customers/${id}`, data);
  },

  // Delete customer
  deleteCustomer: async (id: string): Promise<void> => {
    return apiClient.delete(`/sales/customers/${id}`);
  },

  // Get customer orders
  getCustomerOrders: async (customerId: string): Promise<any[]> => {
    return apiClient.get(`/sales/customers/${customerId}/orders`);
  },

  // Get customer invoices
  getCustomerInvoices: async (customerId: string): Promise<any[]> => {
    return apiClient.get(`/sales/customers/${customerId}/invoices`);
  },

  // =====================================================
  // Leads
  // =====================================================

  // List leads
  listLeads: async (params?: {
    status?: string;
    source?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Lead>> => {
    return apiClient.get('/sales/leads', { params });
  },

  // Get lead by ID
  getLead: async (id: string): Promise<Lead> => {
    return apiClient.get(`/sales/leads/${id}`);
  },

  // Create lead
  createLead: async (data: LeadCreate): Promise<Lead> => {
    return apiClient.post('/sales/leads', data);
  },

  // Update lead
  updateLead: async (id: string, data: Partial<LeadCreate>): Promise<Lead> => {
    return apiClient.put(`/sales/leads/${id}`, data);
  },

  // Delete lead
  deleteLead: async (id: string): Promise<void> => {
    return apiClient.delete(`/sales/leads/${id}`);
  },

  // Convert lead to opportunity
  convertLead: async (id: string): Promise<Opportunity> => {
    return apiClient.post(`/sales/leads/${id}/convert`);
  },

  // =====================================================
  // Opportunities
  // =====================================================

  // List opportunities
  listOpportunities: async (params?: {
    stage?: string;
    customer_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Opportunity>> => {
    return apiClient.get('/sales/opportunities', { params });
  },

  // Get opportunity by ID
  getOpportunity: async (id: string): Promise<Opportunity> => {
    return apiClient.get(`/sales/opportunities/${id}`);
  },

  // Create opportunity
  createOpportunity: async (data: OpportunityCreate): Promise<Opportunity> => {
    return apiClient.post('/sales/opportunities', data);
  },

  // Update opportunity
  updateOpportunity: async (id: string, data: Partial<OpportunityCreate>): Promise<Opportunity> => {
    return apiClient.put(`/sales/opportunities/${id}`, data);
  },

  // Delete opportunity
  deleteOpportunity: async (id: string): Promise<void> => {
    return apiClient.delete(`/sales/opportunities/${id}`);
  },

  // Update opportunity stage
  updateStage: async (id: string, stage: string): Promise<{ message: string }> => {
    return apiClient.post(`/sales/opportunities/${id}/stage`, { stage });
  },

  // =====================================================
  // Quotes
  // =====================================================

  // List quotes
  listQuotes: async (params?: {
    status?: string;
    customer_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Quote>> => {
    return apiClient.get('/sales/quotes', { params });
  },

  // Get quote by ID
  getQuote: async (id: string): Promise<Quote> => {
    return apiClient.get(`/sales/quotes/${id}`);
  },

  // Create quote
  createQuote: async (data: QuoteCreate): Promise<Quote> => {
    return apiClient.post('/sales/quotes', data);
  },

  // Update quote
  updateQuote: async (id: string, data: Partial<QuoteCreate>): Promise<Quote> => {
    return apiClient.put(`/sales/quotes/${id}`, data);
  },

  // Delete quote
  deleteQuote: async (id: string): Promise<void> => {
    return apiClient.delete(`/sales/quotes/${id}`);
  },

  // Send quote
  sendQuote: async (id: string): Promise<{ message: string }> => {
    return apiClient.post(`/sales/quotes/${id}/send`);
  },

  // Accept quote
  acceptQuote: async (id: string): Promise<{ message: string }> => {
    return apiClient.post(`/sales/quotes/${id}/accept`);
  },

  // Reject quote
  rejectQuote: async (id: string): Promise<{ message: string }> => {
    return apiClient.post(`/sales/quotes/${id}/reject`);
  },

  // =====================================================
  // Pipeline
  // =====================================================

  // Get pipeline summary
  getPipelineSummary: async (): Promise<any> => {
    return apiClient.get('/sales/pipeline/summary');
  },

  // Get pipeline by stage
  getPipelineByStage: async (): Promise<any[]> => {
    return apiClient.get('/sales/pipeline/by-stage');
  },

  // Get sales forecast
  getSalesForecast: async (periodDays?: number): Promise<any> => {
    return apiClient.get('/sales/pipeline/forecast', {
      params: { period_days: periodDays },
    });
  },

  // =====================================================
  // Reports
  // =====================================================

  // Get sales report
  getSalesReport: async (
    startDate: string,
    endDate: string
  ): Promise<any> => {
    return apiClient.get('/sales/reports/sales', {
      params: { start_date: startDate, end_date: endDate },
    });
  },

  // Get top customers
  getTopCustomers: async (limit?: number): Promise<any[]> => {
    return apiClient.get('/sales/reports/top-customers', {
      params: { limit },
    });
  },

  // Get top products
  getTopProducts: async (limit?: number): Promise<any[]> => {
    return apiClient.get('/sales/reports/top-products', {
      params: { limit },
    });
  },
};

export default salesApi;
