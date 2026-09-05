import { beforeEach, describe, expect, it, vi } from 'vitest';
import axios from 'axios';
import apiClient, { authAPI, customersAPI, invoicesAPI, ordersAPI, productsAPI, suppliersAPI } from './api';

const interceptorHandlers = vi.hoisted(() => ({
  request: undefined as ((config: { headers: Record<string, string> }) => unknown) | undefined,
  responseSuccess: undefined as ((response: unknown) => unknown) | undefined,
  responseError: undefined as ((error: unknown) => unknown) | undefined,
}));

vi.mock('axios', async () => {
  const actual = await vi.importActual<typeof import('axios')>('axios');
  const storage = new Map<string, string>();
  const localStorageMock = {
    getItem: vi.fn((key: string) => storage.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => storage.set(key, String(value))),
    removeItem: vi.fn((key: string) => storage.delete(key)),
    clear: vi.fn(() => storage.clear()),
  };
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: localStorageMock });
  const requestUse = vi.fn((handler: (config: { headers: Record<string, string> }) => unknown) => {
    interceptorHandlers.request = handler;
    return 0;
  });
  const responseUse = vi.fn((success: (response: unknown) => unknown, error: (error: unknown) => unknown) => {
    interceptorHandlers.responseSuccess = success;
    interceptorHandlers.responseError = error;
    return 0;
  });
  const client = {
    defaults: { headers: { common: {} } },
    interceptors: { request: { use: requestUse }, response: { use: responseUse } },
    get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn(), request: vi.fn(),
  };
  return { ...actual, default: { ...actual.default, create: vi.fn(() => client) } };
});

describe('EOS API client functional contract', () => {
  beforeEach(() => {
    globalThis.localStorage.clear();
    vi.mocked(apiClient.get).mockClear(); vi.mocked(apiClient.post).mockClear();
    vi.mocked(apiClient.put).mockClear(); vi.mocked(apiClient.delete).mockClear(); vi.mocked(apiClient.request).mockClear();
  });

  it('uses the configured API facade for authentication', async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({ data: { data: { access_token: 'access', refresh_token: 'refresh' } } } as never);
    await authAPI.login('user@example.com', 'password');
    expect(apiClient.post).toHaveBeenCalledWith('/auth/login', { email: 'user@example.com', password: 'password' });
  });

  it('supports email verification as a public authentication action', async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({ data: { data: { message: 'Email verified' } } } as never);
    await authAPI.verifyEmail('verification-token');
    expect(apiClient.post).toHaveBeenCalledWith('/auth/verify-email', { token: 'verification-token' });
  });

  it('persists tokens and company context returned by the response interceptor', async () => {
    expect(interceptorHandlers.responseSuccess).toBeDefined();
    await interceptorHandlers.responseSuccess!({ data: { data: { access_token: 'access-1', refresh_token: 'refresh-1', user: { tenant_id: 't1', company_id: 'c1' } } } });
    expect(localStorage.getItem('access_token')).toBe('access-1'); expect(localStorage.getItem('refresh_token')).toBe('refresh-1');
    expect(localStorage.getItem('eos_tenant_id')).toBe('t1'); expect(localStorage.getItem('eos_company_id')).toBe('c1');
  });

  it('attaches the current bearer token to requests', () => {
    localStorage.setItem('access_token', 'access-2');
    const config = interceptorHandlers.request!({ headers: {} });
    expect((config as { headers: Record<string, string> }).headers.Authorization).toBe('Bearer access-2');
  });

  it('refreshes a failed request and rotates both tokens', async () => {
    localStorage.setItem('refresh_token', 'refresh-old');
    vi.mocked(apiClient.post).mockResolvedValueOnce({ data: { data: { access_token: 'access-new', refresh_token: 'refresh-new' } } } as never);
    vi.mocked(apiClient.request).mockResolvedValueOnce({ data: { ok: true } } as never);
    const result = await interceptorHandlers.responseError!({ response: { status: 401 }, config: { url: '/sales/customers', headers: {} } });
    expect(apiClient.post).toHaveBeenCalledWith('/auth/refresh', { refresh_token: 'refresh-old' });
    expect(localStorage.getItem('access_token')).toBe('access-new'); expect(localStorage.getItem('refresh_token')).toBe('refresh-new');
    expect(result).toEqual({ data: { ok: true } });
  });

  it('clears the local session when refresh fails', async () => {
    localStorage.setItem('access_token', 'access-old'); localStorage.setItem('refresh_token', 'refresh-old');
    vi.mocked(apiClient.post).mockRejectedValueOnce(new Error('refresh failed'));
    await expect(interceptorHandlers.responseError!({ response: { status: 401 }, config: { url: '/reports/sales', headers: {} } })).rejects.toBeDefined();
    expect(localStorage.getItem('access_token')).toBeNull(); expect(localStorage.getItem('refresh_token')).toBeNull();
  });

  it('routes customer, supplier and product CRUD through canonical APIs', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { data: [] } } as never);
    vi.mocked(apiClient.post).mockResolvedValue({ data: { data: { id: 'x1' } } } as never);
    vi.mocked(apiClient.put).mockResolvedValue({ data: { data: { id: 'x1' } } } as never);
    vi.mocked(apiClient.delete).mockResolvedValue({ data: { data: { message: 'deleted' } } } as never);
    await customersAPI.getAll({ search: 'Acme' }); await customersAPI.create({ name: 'Acme' }); await customersAPI.update('c1', { name: 'Acme Ltd' }); await customersAPI.delete('c1');
    await suppliersAPI.getAll({ search: 'Vendor' }); await suppliersAPI.create({ name: 'Vendor' }); await suppliersAPI.update('s1', { name: 'Vendor Ltd' }); await suppliersAPI.delete('s1');
    await productsAPI.getAll({ search: 'Widget' }); await productsAPI.create({ name: 'Widget' }); await productsAPI.update('p1', { name: 'Widget Pro' }); await productsAPI.delete('p1');
    expect(apiClient.get).toHaveBeenCalledWith('/sales/customers', { params: { search: 'Acme' } });
  });

  it('routes the commercial sales-order, invoice issue and collection workflow', async () => {
    localStorage.setItem('eos_company_id', 'company-1');
    vi.mocked(apiClient.get).mockResolvedValue({ data: { data: [] } } as never);
    vi.mocked(apiClient.post).mockResolvedValue({ data: { data: { id: 'x1' } } } as never);
    await ordersAPI.getAll(); await ordersAPI.create({ customer_id: 'c1', order_date: '2026-09-05', lines: [] }); await ordersAPI.getById('o1');
    await invoicesAPI.getAll(); await invoicesAPI.create({ customer_id: 'c1', invoice_date: '2026-09-05', lines: [] }); await invoicesAPI.getById('i1');
    await invoicesAPI.issue('i1'); await invoicesAPI.recordPayment('i1', 100, '2026-09-05');
    expect(apiClient.get).toHaveBeenCalledWith('/dynamic/companies/company-1/sales-orders', { params: undefined });
    expect(apiClient.post).toHaveBeenCalledWith('/dynamic/companies/company-1/sales-orders', { customer_id: 'c1', order_date: '2026-09-05', lines: [] });
    expect(apiClient.get).toHaveBeenCalledWith('/dynamic/sales-orders/o1');
    expect(apiClient.get).toHaveBeenCalledWith('/dynamic/companies/company-1/invoices', { params: undefined });
    expect(apiClient.post).toHaveBeenCalledWith('/dynamic/companies/company-1/invoices', { customer_id: 'c1', invoice_date: '2026-09-05', lines: [] });
    expect(apiClient.get).toHaveBeenCalledWith('/dynamic/invoices/i1');
    expect(apiClient.post).toHaveBeenCalledWith('/dynamic/invoices/i1/issue');
    expect(apiClient.post).toHaveBeenCalledWith('/dynamic/invoices/i1/payments', { amount: 100, payment_date: '2026-09-05' });
  });
});

void axios;
