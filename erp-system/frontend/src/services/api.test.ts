import { beforeEach, describe, expect, it, vi } from 'vitest';
import axios from 'axios';
import apiClient, { authAPI, customersAPI, invoicesAPI, ordersAPI, productsAPI, suppliersAPI } from './api';

vi.mock('axios', async () => {
  const actual = await vi.importActual<typeof import('axios')>('axios');
  const client = {
    defaults: { headers: { common: {} } },
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn(), request: vi.fn(),
  };
  return { ...actual, default: { ...actual.default, create: vi.fn(() => client) } };
});

describe('EOS API client functional contract', () => {
  beforeEach(() => { localStorage.clear(); vi.clearAllMocks(); });

  it('uses the configured API facade for authentication', async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({ data: { data: { access_token: 'access', refresh_token: 'refresh' } } } as never);
    await authAPI.login('user@example.com', 'password');
    expect(apiClient.post).toHaveBeenCalledWith('/auth/login', { email: 'user@example.com', password: 'password' });
  });

  it('persists tokens returned by the response interceptor', () => {
    const client = vi.mocked(axios.create).mock.results[0]?.value;
    const [, onSuccess] = client.interceptors.response.use.mock.calls[0] || [];
    onSuccess({ data: { data: { access_token: 'access-1', refresh_token: 'refresh-1' } } });
    expect(localStorage.getItem('access_token')).toBe('access-1');
    expect(localStorage.getItem('refresh_token')).toBe('refresh-1');
  });

  it('attaches the current bearer token to requests', () => {
    localStorage.setItem('access_token', 'access-2');
    const client = vi.mocked(axios.create).mock.results[0]?.value;
    const [onRequest] = client.interceptors.request.use.mock.calls[0] || [];
    const config = onRequest({ headers: {} });
    expect(config.headers.Authorization).toBe('Bearer access-2');
  });

  it('refreshes a failed request and rotates both tokens', async () => {
    localStorage.setItem('refresh_token', 'refresh-old');
    vi.mocked(apiClient.post).mockResolvedValueOnce({ data: { data: { access_token: 'access-new', refresh_token: 'refresh-new' } } } as never);
    vi.mocked(apiClient.request).mockResolvedValueOnce({ data: { ok: true } } as never);
    const client = vi.mocked(axios.create).mock.results[0]?.value;
    const [, onError] = client.interceptors.response.use.mock.calls[0] || [];
    const result = await onError({ response: { status: 401 }, config: { url: '/sales/customers', headers: {} } });
    expect(apiClient.post).toHaveBeenCalledWith('/auth/refresh', { refresh_token: 'refresh-old' });
    expect(localStorage.getItem('access_token')).toBe('access-new');
    expect(localStorage.getItem('refresh_token')).toBe('refresh-new');
    expect(apiClient.request).toHaveBeenCalledWith(expect.objectContaining({ _retry: true, headers: { Authorization: 'Bearer access-new' } }));
    expect(result).toEqual({ data: { ok: true } });
  });

  it('clears the local session when refresh fails', async () => {
    localStorage.setItem('access_token', 'access-old');
    localStorage.setItem('refresh_token', 'refresh-old');
    vi.mocked(apiClient.post).mockRejectedValueOnce(new Error('refresh failed'));
    const client = vi.mocked(axios.create).mock.results[0]?.value;
    const [, onError] = client.interceptors.response.use.mock.calls[0] || [];
    await expect(onError({ response: { status: 401 }, config: { url: '/reports/sales', headers: {} } })).rejects.toBeDefined();
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
    expect(localStorage.getItem('eos_tenant_id')).toBeNull();
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
    expect(apiClient.post).toHaveBeenCalledWith('/sales/customers', { name: 'Acme' });
    expect(apiClient.put).toHaveBeenCalledWith('/sales/customers/c1', { name: 'Acme Ltd' });
    expect(apiClient.delete).toHaveBeenCalledWith('/sales/customers/c1');
    expect(apiClient.get).toHaveBeenCalledWith('/inventory/suppliers', { params: { search: 'Vendor' } });
    expect(apiClient.get).toHaveBeenCalledWith('/inventory/products', { params: { search: 'Widget' } });
  });

  it('fails closed for unavailable order and invoice contracts', async () => {
    await expect(ordersAPI.getAll()).rejects.toThrow(/orders API is not wired/);
    await expect(invoicesAPI.getAll()).rejects.toThrow(/invoices API is not wired/);
  });
});

void axios;
