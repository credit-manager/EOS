import { beforeEach, describe, expect, it, vi } from 'vitest';
import axios from 'axios';
import apiClient, { authAPI, customersAPI, ordersAPI } from './api';

vi.mock('axios', async () => {
  const actual = await vi.importActual<typeof import('axios')>('axios');
  const client = {
    defaults: { headers: { common: {} } },
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    request: vi.fn(),
  };
  return { ...actual, default: { ...actual.default, create: vi.fn(() => client) } };
});

describe('EOS API client', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('uses the configured API facade for authentication', async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({ data: { data: { access_token: 'access', refresh_token: 'refresh' } } } as never);

    await authAPI.login('user@example.com', 'password');

    expect(apiClient.post).toHaveBeenCalledWith('/auth/login', {
      email: 'user@example.com',
      password: 'password',
    });
  });

  it('routes customer CRUD through the canonical sales API', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: { data: [] } } as never);
    vi.mocked(apiClient.post).mockResolvedValueOnce({ data: { data: { id: 'c1' } } } as never);
    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: { data: { id: 'c1' } } } as never);
    vi.mocked(apiClient.delete).mockResolvedValueOnce({ data: { data: { message: 'deleted' } } } as never);

    await customersAPI.getAll({ search: 'Acme' });
    await customersAPI.create({ name: 'Acme' });
    await customersAPI.update('c1', { name: 'Acme Ltd' });
    await customersAPI.delete('c1');

    expect(apiClient.get).toHaveBeenCalledWith('/sales/customers', { params: { search: 'Acme' } });
    expect(apiClient.post).toHaveBeenCalledWith('/sales/customers', { name: 'Acme' });
    expect(apiClient.put).toHaveBeenCalledWith('/sales/customers/c1', { name: 'Acme Ltd' });
    expect(apiClient.delete).toHaveBeenCalledWith('/sales/customers/c1');
  });

  it('fails closed for backend contracts that are intentionally unavailable', async () => {
    await expect(ordersAPI.getAll()).rejects.toThrow(/orders API is not wired/);
    expect(apiClient.get).not.toHaveBeenCalled();
  });
});

void axios;
