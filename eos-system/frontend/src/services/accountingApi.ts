/**
 * EOS System — Accounting API Service
 */

import apiClient from './apiClient';
import type {
  Account,
  AccountCreate,
  JournalEntry,
  JournalEntryCreate,
  TrialBalance,
  IncomeStatement,
  BalanceSheet,
  PaginatedResponse,
} from '../types';

export const accountingApi = {
  // =====================================================
  // Accounts
  // =====================================================

  // List accounts
  listAccounts: async (params?: {
    account_type?: string;
    parent_id?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Account>> => {
    return apiClient.get('/accounting/accounts', { params });
  },

  // Get account by ID
  getAccount: async (id: string): Promise<Account> => {
    return apiClient.get(`/accounting/accounts/${id}`);
  },

  // Create account
  createAccount: async (data: AccountCreate): Promise<Account> => {
    return apiClient.post('/accounting/accounts', data);
  },

  // Update account
  updateAccount: async (id: string, data: Partial<AccountCreate>): Promise<Account> => {
    return apiClient.put(`/accounting/accounts/${id}`, data);
  },

  // Delete account
  deleteAccount: async (id: string): Promise<void> => {
    return apiClient.delete(`/accounting/accounts/${id}`);
  },

  // =====================================================
  // Journal Entries
  // =====================================================

  // List journal entries
  listJournalEntries: async (params?: {
    start_date?: string;
    end_date?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<JournalEntry>> => {
    return apiClient.get('/accounting/journal', { params });
  },

  // Get journal entry by ID
  getJournalEntry: async (id: string): Promise<JournalEntry> => {
    return apiClient.get(`/accounting/journal/${id}`);
  },

  // Create journal entry
  createJournalEntry: async (data: JournalEntryCreate): Promise<JournalEntry> => {
    return apiClient.post('/accounting/journal', data);
  },

  // Post journal entry
  postJournalEntry: async (id: string): Promise<{ message: string }> => {
    return apiClient.post(`/accounting/journal/${id}/post`);
  },

  // Reverse journal entry
  reverseJournalEntry: async (id: string): Promise<{ message: string }> => {
    return apiClient.post(`/accounting/journal/${id}/reverse`);
  },

  // =====================================================
  // Reports
  // =====================================================

  // Get trial balance
  getTrialBalance: async (asOfDate?: string): Promise<TrialBalance> => {
    const params = asOfDate ? { as_of_date: asOfDate } : {};
    return apiClient.get('/accounting/reports/trial-balance', { params });
  },

  // Get income statement
  getIncomeStatement: async (
    startDate: string,
    endDate: string
  ): Promise<IncomeStatement> => {
    return apiClient.get('/accounting/reports/income-statement', {
      params: { start_date: startDate, end_date: endDate },
    });
  },

  // Get balance sheet
  getBalanceSheet: async (asOfDate?: string): Promise<BalanceSheet> => {
    const params = asOfDate ? { as_of_date: asOfDate } : {};
    return apiClient.get('/accounting/reports/balance-sheet', { params });
  },

  // Get cash flow statement
  getCashFlowStatement: async (
    startDate: string,
    endDate: string
  ): Promise<any> => {
    return apiClient.get('/accounting/reports/cash-flow', {
      params: { start_date: startDate, end_date: endDate },
    });
  },

  // Get profit & loss report
  getProfitAndLoss: async (
    startDate: string,
    endDate: string
  ): Promise<any> => {
    return apiClient.get('/accounting/reports/profit-and-loss', {
      params: { start_date: startDate, end_date: endDate },
    });
  },
};

export default accountingApi;
