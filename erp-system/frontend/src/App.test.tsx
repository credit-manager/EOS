import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

type MockClient = {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  put: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
  interceptors: {
    request: { use: ReturnType<typeof vi.fn> };
    response: { use: ReturnType<typeof vi.fn> };
  };
};

const mockedClient = vi.hoisted<MockClient>(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
  interceptors: {
    request: { use: vi.fn() },
    response: { use: vi.fn() },
  },
}));

vi.mock('axios', () => ({
  default: { create: vi.fn(() => mockedClient) },
}));

async function loadApi() {
  vi.resetModules();
  return import('./services/api');
}

describe('EOS frontend functional API flows', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(globalThis, 'window', {
      configurable: true,
      value: { location: { origin: 'http://localhost:3000' }, dispatchEvent: vi.fn() },
    });
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      value: { getItem: vi.fn(), setItem: vi.fn(), removeItem: vi.fn() },
    });
  });

  afterEach(() => vi.restoreAllMocks());

  it('uses the canonical same-origin API base and Arabic headers', async () => {
    const axios = await import('axios');
    await loadApi();
    expect(vi.mocked(axios.default.create)).toHaveBeenCalledWith({
      baseURL: 'http://localhost:3000/api/v1',
      headers: { 'Content-Type': 'application/json', 'Accept-Language': 'ar' },
    });
  });

  it('maps supported customer, supplier, product and report actions to backend contracts', async () => {
    const api = await loadApi();

    api.customersAPI.getAll({ search: 'acme' });
    api.customersAPI.getById('c1');
    api.customersAPI.create({ name: 'Acme' });
    api.customersAPI.update('c1', { name: 'Updated' });
    api.customersAPI.delete('c1');
    api.suppliersAPI.getAll();
    api.productsAPI.getAll();
    api.reportsAPI.profitAndLoss();

    expect(mockedClient.get).toHaveBeenCalledWith('/sales/customers', { params: { search: 'acme' } });
    expect(mockedClient.get).toHaveBeenCalledWith('/sales/customers/c1');
    expect(mockedClient.post).toHaveBeenCalledWith('/sales/customers', { name: 'Acme' });
    expect(mockedClient.put).toHaveBeenCalledWith('/sales/customers/c1', { name: 'Updated' });
    expect(mockedClient.delete).toHaveBeenCalledWith('/sales/customers/c1');
    expect(mockedClient.get).toHaveBeenCalledWith('/inventory/suppliers', { params: undefined });
    expect(mockedClient.get).toHaveBeenCalledWith('/inventory/products', { params: undefined });
    expect(mockedClient.get).toHaveBeenCalledWith('/reports/profit-and-loss', { params: undefined });
  });

  it('fails closed for backend resources that are intentionally not wired', async () => {
    const api = await loadApi();
    await expect(api.ordersAPI.getAll()).rejects.toThrow(/orders API is not wired/i);
    await expect(api.invoicesAPI.getAll()).rejects.toThrow(/invoices API is not wired/i);
    expect(mockedClient.get).not.toHaveBeenCalled();
  });

  it('does not attempt refresh for authentication 401 responses', async () => {
    await loadApi();
    const [, onRejected] = mockedClient.interceptors.response.use.mock.calls[0];
    const error = { response: { status: 401 }, config: { url: '/auth/login' } };
    await expect(onRejected(error)).rejects.toEqual(error);
    expect(mockedClient.post).not.toHaveBeenCalled();
  });
});
